# Graph Schema

`graph.json` contains:

- `graph_version`: integer, currently `1`
- `source_commit`: Git commit SHA or `UNKNOWN`
- `generated_at`: UTC timestamp
- `repository_root`: absolute repository root
- `nodes`: array
- `edges`: array

Node fields:

- `id`: stable string
- `kind`: directory | file | module | class | function | method | import | export | cli_command | config_schema | environment_variable | test_file | external_dependency | generated_artifact
- `path`: repository-relative file or directory path when applicable
- `name`: symbol or display name
- `language`: optional language
- `evidence`: list of file:line or file:symbol entries
- `confidence`: high | medium | low
- `metadata`: object

Edge fields:

- `source`: node id
- `target`: node id
- `kind`: imports | calls | inherits | config_flow | cli_dispatch | tests | owns_layer
- `confidence`: high | medium | low
- `evidence`: list
- `caveat`: optional limitation

Do not represent guessed edges as high confidence.
