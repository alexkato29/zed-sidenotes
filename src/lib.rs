use zed_extension_api::{self as zed, LanguageServerId, Result};

struct Sidenotes;

impl zed::Extension for Sidenotes {
    fn new() -> Self {
        Sidenotes
    }

    fn language_server_command(
        &mut self,
        _id: &LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<zed::Command> {
        let command = worktree
            .which("zed-sidenotes")
            .ok_or("zed-sidenotes not found on PATH")?;
        Ok(zed::Command {
            command,
            args: vec![],
            env: worktree.shell_env(),
        })
    }
}

zed::register_extension!(Sidenotes);
