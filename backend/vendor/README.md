# Optional backend dependencies

`YOLOX` retains the existing third-party Git reference at commit
`6ddff4824372906469a7fae2dc3206c7aa4bbaee`, relocated from the repository root.
It is currently an empty/uninitialized reference; the repository does not provide its
submodule URL. No URL is guessed and no dependency/model is automatically executed.

The application-owned perception scripts and weights are in `backend/taxi/perception`.
The tested simulation uses `taxi.supervisor` and `taxi.navigation` without YOLOX.
