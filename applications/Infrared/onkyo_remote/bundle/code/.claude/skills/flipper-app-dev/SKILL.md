---
name: flipper-app-dev
description: Build, lint, and debug Flipper Zero applications (.fap) with ufbt. Use when working on application.fam manifests, furi/GUI/infrared/SubGHz APIs, linker errors about missing firmware symbols, FAP icons, or when running ufbt build/launch/cli/update in this repo.
---

# Flipper Zero app development

External apps (`.fap`) are built with `ufbt`, which keeps the SDK and ARM
toolchain in `~/.ufbt` — never in the repo. One app per project directory,
rooted at the `application.fam`.

## Commands

Run these from the directory holding `application.fam`:

| Command        | Effect                                                |
| -------------- | ----------------------------------------------------- |
| `ufbt`         | Build → `dist/<appid>.fap`                            |
| `ufbt launch`  | Build, upload over USB, and start it on the Flipper   |
| `ufbt cli`     | Flipper serial console (`ir rx`, `log`, `ps`, `free`) |
| `ufbt lint`    | clang-format check (needs the `clang-format` package) |
| `ufbt format`  | Rewrite sources to firmware style                     |
| `ufbt update`  | Fetch a newer SDK; re-check the build after           |
| `ufbt -c`      | Clean                                                 |
| `ufbt cdb`     | Regenerate `.vscode/compile_commands.json`            |

`ufbt create APPID=myapp` scaffolds a fresh app into the current directory.

Always build after editing — `ufbt` is fast once the SDK is cached, and the
APPCHK step catches API-version drift that a source read will not.

## The API symbol table is the main gotcha

A `.fap` links against a fixed table of symbols the firmware exports, listed in
`~/.ufbt/current/sdk_headers/f7_sdk/targets/f7/api_symbols.csv`. A header
existing in the SDK does **not** mean the function is callable.

Before using an unfamiliar SDK function, check:

```bash
grep -E "^Function,.,<name>," ~/.ufbt/current/sdk_headers/f7_sdk/targets/f7/api_symbols.csv
```

If it is absent, the code compiles and then fails at link. The fix is to
statically link the library providing it, via the manifest:

```python
fap_libs=["infrared"]
```

Available prebuilt archives are in `~/.ufbt/current/lib/` (`libinfrared.a`,
`libsubghz.a`, `libnfc.a`, `libtoolbox.a`, …); strip the `lib`/`.a` for the
`fap_libs` name. This costs flash, so only link what is genuinely missing.

Check before reaching for `fap_libs`: this repo carried `fap_libs=["infrared"]`
for a symbol that turned out to be exported after all, and the dead static link
cost 21 KB — 29,892 bytes against 8,876. Grep `api_symbols.csv` first, and only
link a library when the build actually fails without it.

## Manifest

```python
App(
    appid="my_app",                  # must match ^[a-z0-9_]+$
    name="My App",                   # shown in the Flipper menu
    apptype=FlipperAppType.EXTERNAL,
    entry_point="my_app_main",       # int32_t fn(void*)
    requires=["gui", "notification"],
    stack_size=2 * 1024,
    fap_category="Infrared",         # becomes the SD-card subfolder
    fap_icon="images/icon_10px.png", # 10x10, 1-bit PNG, or the build fails
    fap_icon_assets="images",
    fap_version="0.1",
)
```

The icon really must be 10x10 and 1-bit — an 8-bit PNG is rejected. `ImageMagick`
or a few lines of `zlib`+`struct` will produce one.

## Runtime rules

- Entry point is `int32_t name(void* p)`; `UNUSED(p)` if ignored.
- Everything acquired must be released: `furi_record_open` ↔
  `furi_record_close`, `*_alloc` ↔ `*_free`, and view ports must be removed from
  the GUI before being freed. Leaks survive the app and degrade the whole system
  until reboot.
- Draw and input callbacks run on the **GUI thread**, not yours. Guard shared
  state with a `FuriMutex`, and keep draw callbacks free of blocking work.
- Push input events into a `FuriMessageQueue` and handle them on your own
  thread; do not transmit or do I/O inside the input callback.
- `stack_size` is per-app and small. Deep recursion or large stack buffers cause
  a crash that looks like a random reboot — heap-allocate instead.
- `FURI_LOG_I(TAG, ...)` output is visible via `ufbt cli` → `log`.

## Debugging

`ufbt cli` then `log` gives a live view. For a crash, the Flipper shows a
stack trace; `ufbt debug` attaches GDB if an SWD probe is connected.

If a build suddenly fails after `ufbt update`, the firmware API version moved —
check the APPCHK line at the end of the build for the expected `API:` value.
