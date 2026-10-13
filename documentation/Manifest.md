# Manifest

Each entry submitted to this catalog is defined by a manifest file called `manifest.yml`. The CI uses it to fetch the code, check it and package it, and the package is then uploaded to the qUnleashed catalog server, which manages builds for every SDK it keeps.

The full path of a manifest tells what the entry is, where it belongs and how it is called:

| Kind | Path | Installed to |
| --- | --- | --- |
| App | `applications/<Category>[/<Subcategory>]/<appid>/manifest.yml` | `/ext/apps/<Category>[/<Subcategory>]/<appid>.fap` |
| Menu style | `menustyles/<Category>/<appid>/manifest.yml` | `/ext/apps_data/loader/plugins/<appid>.fal` |
| Animation | `animations/<Pack>[/<Collection>]/<Name>/manifest.yml` | `/ext/dolphin/<Name>` |

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

If your `application.fam` defines multiple apps, specify the one this manifest is for with the `id` field. This is always the case for menu styles kept together in one repository: each style gets its own manifest with its `id`.

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

The CI sends the animation to the catalog server as one bundle, `manifest.yml` with `meta.txt` and the frames, to `/api/v1/animations/version/bundle`.

### Source code location

The source code origin is specified in the `sourcecode` section. It contains the `type` field, which must be set to `git`. It must also contain the `location` section, which specifies the repository location.

 * `origin` is the git URL of the repository. Required.
 * `commit_sha` is the full SHA of the commit that contains the code being submitted. Required, except for trusted repositories, see [Following HEAD](#following-head).
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

### Following HEAD

For trusted repositories, such as [all-the-plugins](https://github.com/xMasterX/all-the-plugins) and those of friends of the project, `commit_sha` may be left out:

```yaml
sourcecode:
  type: git
  location:
    origin: https://github.com/xMasterX/all-the-plugins.git
    subdir: base_pack/esp32_wifi_marauder
```

Such an entry is built from the repository HEAD. The CI re-reads it once a day and publishes a new version when its version changes. Whether a repository is trusted is decided at review; for everyone else `commit_sha` is required.

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

The bundler installs the Unleashed SDK for `ufbt` itself. To keep it apart from the SDK you use day to day, point `UFBT_HOME` into the virtual environment.

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

Then run the validation script, passing it the path to your manifest file. For an app or a menu style:

```bash
python3 tools/bundle.py --nolint applications/CATEGORY/APPID/manifest.yml bundle.zip
```

`BUNDLE_SDK_CHANNEL=dev` checks against the Development SDK instead of Release.

For an animation, or to check only the paths and fields of any manifest:

```bash
python3 tools/publish.py check animations/PACK/NAME/manifest.yml
python3 tools/publish.py check --offline applications/CATEGORY/APPID/manifest.yml
```

On Windows, use `python` instead of `python3` if `python3` is not available.

If there are any errors, the script will print them and exit with non-zero exit code. **Be sure to fix all errors before submitting.**

## Build process

1. A pull request runs `tools/bundle.py` for every changed app and menu style manifest, and `tools/publish.py check` for animations. Nothing is submitted.
2. A push to `main` submits every changed manifest to the catalog server without building it in CI, since the server builds for every SDK itself: app and menu style sources to `/api/v1/sources/upload`, animation bundles to `/api/v1/animations/version/bundle`. A changed file next to an animation manifest counts as a change of that animation. A deleted app manifest hides the app. Nothing is submitted while the `QU_CATALOG_URL` variable or the `QU_CI_TOKEN` secret is not set.
3. Once a day, every manifest without `commit_sha` is processed again from the repository HEAD.
4. The server builds what it receives for its Release and Development SDK; an entry is shown in qUnleashed once it has a successful build for the user's firmware.
