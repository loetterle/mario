import typing as t

import attr
import click
import marshmallow
from marshmallow import fields


TYPES = {t.__name__: t for t in [int, str, bool, float]}


class TypeField(marshmallow.fields.Field):
    def __init__(self, *args, **kwargs):
        self.default = kwargs.get("default", marshmallow.missing)
        super().__init__(*args, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return TYPES[value]
        except KeyError:
            if self.default == marshmallow.missing:
                raise
            return self.default

    def _jsonschema_type_mapping(self):
        d = {"type": "abcd"}

        if "description" in self.metadata.keys():
            d["description"] = self.metadata["description"]
        return d


class OptionNameField(marshmallow.fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        return [value]
        if not value.startswith("-"):
            raise marshmallow.ValidationError(
                f'{value} is an option, so must start with "-".'
            )
        return [value]

    def _jsonschema_type_mapping(self):
        return {"type": "string"}


class ArgumentNameField(marshmallow.fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        return [value]

    def _jsonschema_type_mapping(self):
        return {"type": "string"}


class AnyField(marshmallow.fields.Field):
    def _jsonschema_type_mapping(self):
        return {}


class OptionSchema(marshmallow.Schema):
    param_decls = OptionNameField(
        data_key="name",
        metadata={"description": "Name of the option. Usually prefixed with - or --."},
    )
    typex = TypeField(
        metadata={"description": f'Name of the type. {", ".join(TYPES)} accepted.'}
    )
    is_flag = fields.Boolean(
        default=False, metadata={"description": "Whether the option is a boolean flag."}
    )
    help = fields.String(
        default=None, metadata={"description": "Documentation for the option."}
    )
    hidden = fields.Boolean(
        default=False,
        metadata={"description": "Whether the option is hidden from help."},
    )
    required = fields.Boolean(
        default=False, metadata={"description": "Whether the option is required."}
    )
    nargs = fields.Integer(
        metadata={"description": "Number of instances expected. Pass -1 for variadic."}
    )
    multiple = fields.Boolean(
        metadata={"description": "Whether multiple values can be passed."}
    )
    default = AnyField(default=None, metadata={"description": "Default value."})

    @marshmallow.post_load()
    def make_option(self, validated, partial, many):
        return click.Option(**validated)


class ArgumentSchema(marshmallow.Schema):
    param_decls = ArgumentNameField(
        data_key="name", metadata={"description": "Name of the argument."}
    )
    type = TypeField(
        default=str,
        metadata={"description": f'Name of the type. {", ".join(TYPES)} accepted.'},
    )
    required = fields.Boolean(
        default=True, metadata={"description": "Whether the argument is required."}
    )
    nargs = fields.Integer(
        default=None,
        metadata={"description": "Number of instances expected. Pass -1 for variadic."},
    )

    @marshmallow.post_load()
    def make_argument(self, validated, partial, many):
        return click.Argument(**validated)


@attr.dataclass
class RemapParam:
    new: str
    old: str


class RemapParamSchema(marshmallow.Schema):
    new = fields.String(metadata={"description": "New name of the parameter."})
    old = fields.String(metadata={"description": "Old name of the parameter."})

    @marshmallow.post_load()
    def make_remap(self, validated, partial, many):
        return RemapParam(**validated)


@attr.dataclass
class CommandStage:
    command: str
    remap_params: t.List[RemapParam]
    params: t.Dict[str, str]


class CommandStageSchema(marshmallow.Schema):
    command = fields.String(metadata={"description": "Name of the base command"})
    remap_params = fields.List(
        fields.Nested(RemapParamSchema),
        missing=list,
        metadata={
            "description": "Provide new names for the parameters, different from the base command parameters' names"
        },
    )
    params = fields.Dict(
        missing=dict,
        metadata={
            "description": "Mapping from base command param name (str) to value (str)."
        },
    )

    @marshmallow.post_load()
    def make(self, validated, partial, many):
        return CommandStage(**validated)


@attr.dataclass
class CommandTestSpec:
    invocation: t.List[str]
    input: str
    output: str


class CommandTestSpecSchema(marshmallow.Schema):
    invocation = fields.List(
        fields.String(),
        metadata={
            "description": "Command line arguments to mario. (Don't include `mario`.)"
        },
    )
    input = fields.String(
        metadata={"description": "String passed on stdin to the program."}
    )
    output = fields.String(
        metadata={"description": "Expected string output from the program."}
    )

    @marshmallow.post_load()
    def make(self, validated, partial, many):
        return CommandTestSpec(**validated)


@attr.dataclass
class CommandSpec:
    name: str
    short_help: t.Optional[str]
    help: t.Optional[str]
    arguments: t.List[click.Argument]
    options: t.List[click.Option]
    stages: t.List[CommandStage]
    inject_values: t.List[str]
    test_specs: t.List[CommandTestSpec]
    section: str


class CommandSpecSchema(marshmallow.Schema):
    name = fields.String(metadata={"description": "Name of the new command."})
    help = fields.String(
        default=None,
        missing=None,
        metadata={
            "description": "Long-form documentation of the command. Will be interpreted as ReStructuredText markup."
        },
    )
    short_help = fields.String(
        default=None,
        missing=None,
        metadata={"description": "Single-line CLI description."},
    )
    arguments = fields.List(
        fields.Nested(ArgumentSchema),
        missing=list,
        metadata={"description": "Arguments accepted by the new command."},
    )
    options = fields.List(
        fields.Nested(OptionSchema),
        missing=list,
        metadata={"description": "Options accepted by the new command."},
    )
    stages = fields.List(
        fields.Nested(CommandStageSchema),
        data_key="stage",
        metadata={
            "description": "List of pipeline command stages that input will go through."
        },
    )
    inject_values = fields.List(
        fields.String(),
        missing=list,
        metadata={
            "description": (
                "CLI parameters to be injected into the local namespace, accessible by the executing commands."
            )
        },
    )
    test_specs = fields.List(
        fields.Nested(CommandTestSpecSchema),
        missing=list,
        data_key="test",
        metadata={"description": "List of specifications to test the new command."},
    )
    section = fields.String(
        missing=None,
        metadata={
            "description": "Name of the documentation section in which the new command should appear."
        },
    )

    @marshmallow.post_load()
    def make(self, validated, partial, many):
        return CommandSpec(**validated)
