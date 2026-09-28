# LSP-vibescript

Connects Sublime Text to the [Vibescript](https://github.com/xipkit/vibescript)
language server: diagnostics, hover documentation, completions, and symbol
navigation through `vibes lsp`.

## Prerequisites

- [LSP](https://packagecontrol.io/packages/LSP) installed in Sublime Text
- The [Vibescript](https://github.com/mgomes/sublime-vibescript) package for
  `.vibe` syntax support
- The `vibes` binary available on your `PATH`

Supports the Rust implementation of Vibescript v0.80.0. Install its CLI and
language server with:

```sh
cargo install --git https://github.com/xipkit/vibescript --tag v0.80.0 vibes
```

Add Cargo's bin directory (`~/.cargo/bin` by default) to your editor's `PATH`.
The server command remains `vibes lsp`. Replace any path to the retired Go binary.

## Development install

1. Clone this repo into `~/Library/Application Support/Sublime Text/Packages/` as `LSP-vibescript`:

   ```sh
   git clone https://github.com/mgomes/LSP-vibescript.git \
     "$HOME/Library/Application Support/Sublime Text/Packages/LSP-vibescript"
   ```

2. Restart Sublime Text

## Configuration

The default language server command is:

```json
["vibes", "lsp"]
```

Override it in `Preferences > Package Settings > LSP-vibescript > Settings`
if your `vibes` binary lives elsewhere.
