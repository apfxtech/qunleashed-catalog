# Manifest

Each entry submitted to this catalog is defined by a manifest file called `manifest.yml`. The CI uses it to fetch the code, check it and assemble the entry's bundle: `bundle/` and `bundle.json` next to the manifest. The bundle is sent to the qUnleashed catalog server, which builds it in the latest Unleashed firmware with fbt and publishes it.

The full path of a manifest tells what the entry is, where it belongs and how it is called:

| Kind | Path | Installed to |
| --- | --- | --- |
| App | `applications/<Category>[/<Subcategory>]/<appid>/manifest.yml` | `/ext/apps/<Category>[/<Subcategory>]/<appid>.fap` |
| Menu style | `menustyles/<Category>/<appid>/manifest.yml` | `/ext/apps_data/loader/plugins/<appid>.fal` |
| Animation | `animations/<Pack>[/<Collection>]/<Name>/manifest.yml` | `/ext/dolphin/<Name>` |

Once a day app-stream goes through the manifests of [flipper-application-catalog](https://github.com/flipperdevices/flipper-application-catalog). One for an app that has no manifest here is copied to the path it has there, `applications/<Category>/<appid>/manifest.yml`, in the top folder of the category. Ours is replaced by the official one when it is, byte for byte, a version the official manifest once was: an unchanged copy follows the official catalog, and a manifest we edited, or one pointing at a fork, stays as it is. Nothing is deleted.

## Minimal manifest example

Here is a minimal example of an app manifest. It is expected that some of the fields are specified in the `application.fam` file in the app's source code repository. Namely, `application.fam` should contain `name`, `appid` (set to "example_subghz_app"), `fap_category` (set to "Sub-GHz"), `fap_version`, `fap_author`, and `fap_icon` fields.

The repository should also contain `README.md`, `docs/changelog.md` files, and `screenshots/ss0.png` files.

See [Manifest structure](#manifest-structure) for more details on those fields.

```yaml
sourcecode:
  type: git
  location:
    origin: https://github.com/example/test.git
    commit_sha: bf7019d16d7b50f6a98cc3abdac38c53952a4f30
short_description: Test app
description: "@README.md"
changelog: "@./docs/changelog.md"
screenshots:
  - screenshots/ss0.png
```

This manifest must be placed in the `applications/Sub-GHz/example_subghz_app/manifest.yml` file.

More samples: [app](../example/manifest.yml), [menu style](../example/menustyle/manifest.yml), [animation](../example/animation/manifest.yml).


## Categories

### Apps

The top-level category must be one of the following:

 - **Sub-GHz**: Apps that use Sub-GHz radio.
 - **RFID**: Apps built for low-frequency RFID subsystem.
 - **NFC**: Apps for NFC subsystem.
 - **Infrared**: Infrared-related apps.
 - **GPIO**: Apps utilizing GPIO pins.
 - **iButton**: Apps that use iButton/OneWire subsystem.
 - **USB**: USB-related apps.
 - **Games**: Games.
 - **Media**: Media apps.
 - **Tools**: Utility apps.
 - **Bluetooth**: Bluetooth LE apps.

Inside it, a subcategory may be used, as Unleashed firmware lays its apps out on the SD card. Subcategories in use:

 - **GPIO**: `ESP32`, `ESP8266`, `GPS`, `NRF24`, `Programmers`, `Sensors`, `UART`, `VGM`
 - **Games**: `Arcade`, `Board`, `Puzzle`, `Simulation`
 - **NFC**: `Access`, `Gaming`, `MIFARE`
 - **Media**: `Instruments`, `Players`
 - **Sub-GHz**: `Analyzers`
 - **Tools**: `Calculators`, `Clocks`, `Crypto`, `Editors`, `Timers`

Prefer an existing subcategory; a new one is created by the first manifest placed in it, so a new one is agreed on at review. `fap_category` in `application.fam` may stay the top-level name: when it differs from the path, the manifest `category` must be the full path, for example `category: "GPIO/ESP32"`.

### Menu styles

 - **Layouts**: Menu layouts.
 - **Themes**: Look of the existing layouts.
 - **Functional**: Styles that add behaviour, such as favorites.
 - **Animated**: Styles with animation.

### Animations

The folder under `animations` is the pack the animation belongs to: the firmware or the artist it comes from, optionally with a collection inside, for example `animations/Kuronons/CP77/Kuronons_CP77_Arasaka_128x64`. The animation folder name is the name it gets on the SD card, so it must be unique across all packs.

 - **OFW**: animations shipped with the official firmware.
 - **Unleashed**: animations Unleashed firmware adds on top of OFW.
 - **Momentum**: animations Momentum firmware adds on top of OFW.
 - **Talking-Sasquach**, **Kuronons**, **Stopoxy**, **DoobTheGoober**: artists' packs.

An animation shared by several firmwares is listed once, in the first pack that ships it: Unleashed ships the OFW animations unchanged, and Momentum ships them with a shorter `Duration` only.


## Manifest structure

A manifest is a YAML file that points to the source code repository and provides additional information. Note that required fields that are not specified in the manifest must be specified in the `application.fam` file in the source code repository.

### Apps and menu styles

| Field | Required? | Description | Corresponding field in `application.fam` |
| --- | --- | --- | --- |
| `sourcecode` | Yes | Source code location. See [Source code location](#source-code-location). | None |
| `screenshots` | Yes | A list of paths to screenshot images in the source code repo. See [Screenshots](#screenshots). | None |
| `changelog` | Yes | Changelog. Supports Markdown formatting and file inclusion. [Details](#loading-values-from-files). | None |
| `short_description` | Yes | Short description, plain text. | `fap_description` |
| `description` | Yes | Description. Supports limited Markdown. [Details](#loading-values-from-files). | None |
| `name` | Yes | Name. | `name` |
| `id` | Yes | ID. A lowercase string with no spaces. Must be globally unique. | `appid` |
| `category` | Yes | Category. Must match the manifest location within this repo. | `fap_category` |
| `version` | Yes | Version, in format "major.minor". | `fap_version` |
| `author` | No | Author, as one or more `@name`. | `fap_author` |
| `icon` | Apps only | Icon. Must be 10x10px 1-bit .png file. | `fap_icon` |
| `targets` | No | A list of targets this entry supports. See [documentation on FAM App Manifests](https://developer.flipper.net/flipperzero/doxygen/app_manifests.html) for more. By default - includes all targets. | `targets` |

**It is recommended to specify as many fields as possible in `application.fam` and not in `manifest.yml`, to avoid duplication and keep the manifest file short.**

### The first App()

**The first `App()` in `application.fam` is the entry's app.** Every later `EXTERNAL` app is another build of it, offered beside it (ProtoPirate Extra beside ProtoPirate); a `PLUGIN` is built into the app that requires it. If your `application.fam` defines several apps, the one this manifest is for, its `id`, must come first.

Menu styles kept together in one repository are the exception: each style gets its own manifest with its `id`, and its bundle gets an `application.fam` with that style alone.

### Animations

| Field | Required? | Description |
| --- | --- | --- |
| `sourcecode` | Yes | Where the folder with `meta.txt` and `frame_*.bm` is. See below. |
| `short_description` | No | Short description, plain text. |
| `description` | No | Description. Supports limited Markdown and file inclusion. |
| `author` | No | Author, as one or more `@name`. |
| `weight` | No | How often the animation is picked, as `Weight` in `dolphin/manifest.txt`. |
| `min_butthurt`, `max_butthurt` | No | Mood range the animation is shown in, as `Min butthurt` / `Max butthurt`. |
| `min_level`, `max_level` | No | Dolphin level range the animation is shown in, as `Min level` / `Max level`. |

The animation needs no version: any change to its files is a new version.

An animation is always the same thing: a folder with `meta.txt` and compiled `frame_*.bm` files, exactly as it lies in `/ext/dolphin/<Name>` on the SD card. The manifest says where that folder is, in one of two ways, and the CI treats both alike.

**In another repository.** `origin`, `commit_sha` and `subdir` point at the folder, as for an app:

```yaml
sourcecode:
  type: git
  location:
    origin: https://github.com/stopoxy/FZAnimations.git
    commit_sha: e73a939ed2d5dedcddb1bddd4d23cf091b56e5fc
    subdir: stopoxy_goku_128x64
author: "@stopoxy"
```

**Next to the manifest.** Without `origin`, `subdir` is relative to the manifest's own folder, and the files are committed to this repository beside `manifest.yml`. Use it when the source has no compiled folder to point at, such as firmware animations kept as PNG or animations shipped only as zip files:

```
animations/OFW/L1_Akira_128x64/
├── manifest.yml
├── meta.txt
├── frame_0.bm
└── ...
```

```yaml
sourcecode:
  type: git
  location:
    subdir: .
weight: 3
min_butthurt: 0
max_butthurt: 8
min_level: 1
max_level: 3
```

PNG frames are not accepted: compile them first, for example with `python3 scripts/assets.py dolphin` from the firmware or the `ufbt` SDK.

The CI sends the animation to the catalog server as a bundle folder: `meta.txt` and the frames.

### Source code location

The source code origin is specified in the `sourcecode` section. It contains the `type` field, which must be set to `git`. It must also contain the `location` section, which specifies the repository location.

 * `origin` is the git URL of the repository. Required.
 * `commit_sha` is the full SHA of the commit that contains the code being submitted. Required, except for trusted repositories, see [Trusted repositories](#trusted-repositories).
 * `subdir` is optional and specifies the subdirectory within the repository where the entry is located. If `subdir` is not specified, the root of the repository is used. This is useful if the repository contains several apps or animations.

Example:

```yaml
sourcecode:
  type: git
  location:
    origin: https://github.com/example/test.git
    commit_sha: 520d9f1f04a5fcc67d20c759509ba7fe3d3f9091
    subdir: metronome
```

### Trusted repositories

For trusted repositories, such as [all-the-plugins](https://github.com/xMasterX/all-the-plugins) and those of friends of the project, `commit_sha` may be left out:

```yaml
sourcecode:
  type: git
  location:
    origin: https://github.com/xMasterX/all-the-plugins.git
    subdir: base_pack/esp32_wifi_marauder
```

Once a day app-stream writes `commit_sha` in: the last commit on the repository HEAD that changed the entry's folder, and it keeps moving it there. Publish then sends the entry like any other changed manifest, so every manifest names the code the catalog holds. Trusted repositories are listed in [`trusted.yml`](../trusted.yml), and only the maintainers add to it; for everyone else `commit_sha` is required and moves by pull request.

### Missing metadata

Some sources, such as [all-the-plugins](https://github.com/xMasterX/all-the-plugins), carry code but no catalog metadata. An entry from a repository in `trusted.yml` is published with what it has: no screenshots, a `short_description` from `fap_description` or the name, a `description` from the short one, a `changelog` of `v<version>`. The check of a pull request names what is missing as warnings. Nothing is added to the source repository. This is how the catalog lists apps that exist only in all-the-plugins, and apps whose copy there is patched for Unleashed in place of the original upstream.

### Version

The version is used to determine whether a new version is available for installation on the device. All submitted updates must use a higher version number than the previous one, otherwise the update will be rejected.

The version is specified in the `version` field. It must be in format `major.minor`. For example, `1.0` or `2.3`. If not specified in the YAML manifest, the version is taken from `application.fam` file in the source code repository. That version is also embedded into the binary, so to avoid confusion and build errors, it is recommended to specify the version in `application.fam` and not in `manifest.yml`.

### Loading values from files

Some fields support loading their values from files in the source code repository. This is useful for fields that contain large amounts of text, such as `description` or `changelog`.

To load a value from a file, specify the field value as a string starting with `@` followed by the path to the file in the repository. The path is relative to the source code folder, which may be specified in the `location.subdir` field. Example:

```yaml
...
description: "@README.md"
changelog: "@./docs/changelog.md"
...
```

### Markdown support

For fields that support loading values from files, Markdown formatting is supported. However, only a subset of Markdown features is allowed:

 - Headers of levels 1-2
 - **Bold** and _italic_ text
 - Lists
 - Links - automatic and inline

## Screenshots

Apps and menu styles must contain at least one screenshot. Screenshots are specified in the `screenshots` section of the manifest as a list of screenshot paths.

**Screenshots must be created using the qFlipper screenshot feature.** Please don't change their resolution or format.

## Validating manifest

You can check your manifest file for validity before submitting it. First, set up a virtual Python environment with the required dependencies from your local checkout of this repository.

On Linux, macOS, or WSL:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r tools/requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r tools\requirements.txt
```

On Windows Command Prompt:

```bat
python -m venv venv
venv\Scripts\activate.bat
python -m pip install -r tools\requirements.txt
```

The check builds an app with `ufbt` against the Unleashed SDK. To keep that SDK apart from the one you use day to day, point `UFBT_HOME` into the virtual environment, then install it.

On Linux, macOS, or WSL:

```bash
export UFBT_HOME="$PWD/venv/ufbt"
```

On Windows PowerShell:

```powershell
$env:UFBT_HOME = Join-Path (Get-Location) "venv\ufbt"
```

On Windows Command Prompt:

```bat
set UFBT_HOME=%CD%\venv\ufbt
```

```bash
ufbt update --index-url https://up.unleashedflip.com/directory.json --channel dev
```

The development channel is the one the server builds on. Then run the check from the root of your checkout, passing it the path to your manifest file. For an app, `--build` builds it as the pull request does, within 60 seconds:

```bash
python3 tools/publish.py check --build applications/CATEGORY/APPID/manifest.yml
```

For a menu style or an animation, or to check only the paths and fields of any manifest:

```bash
python3 tools/publish.py check animations/PACK/NAME/manifest.yml
python3 tools/publish.py check --offline applications/CATEGORY/APPID/manifest.yml
```

On Windows, use `python` instead of `python3` if `python3` is not available.

If there are any errors, the script will print them and exit with non-zero exit code. **Be sure to fix all errors before submitting.**

## Build process

Four workflows, each with one task:

1. **pull-request** runs `tools/publish.py check --build` for every changed manifest: every rule above, the apps `application.fam` gives the server, and a `ufbt` build against the development SDK of Unleashed, within 60 seconds, for an app from a repository outside `trusted.yml`. The result is a comment on the pull request and the summary of the run. Nothing is published.
2. **app-stream** runs once a day. It adds the official catalog's manifests we have none of, updates our unchanged copies of the others, and pins the entries of trusted repositories to their latest commit. It writes manifests only.
3. **publish** runs on every push to `main`, a merged pull request and app-stream's commit alike. The manifests changed since the last commit the server took are assembled into `bundle/` and `bundle.json` next to the manifest and, when they differ from what this repository holds, sent in batches to every catalog server listed in [`servers.yml`](../servers.yml), a domain each; the CI then commits them. A deleted manifest takes its entry out of every server. The tag `published` marks the last commit all the servers took, so a run that could not reach one of them is caught up by the next one.
4. **bootstrap** is started by hand by a code owner, with the address of a catalog server and a mode: `update` sends what the server does not hold or holds at another version, `force` sends every entry.

The server builds every app in the latest Unleashed firmware with fbt, and keeps the last version of every entry; its history is this repository's. An app from a repository outside `trusted.yml` must also build with `ufbt`, as it does in the official catalog: that is what the pull request checks. The firmware's core contributors, listed in `trusted.yml`, may publish apps that need the whole firmware tree.
