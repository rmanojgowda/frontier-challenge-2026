# Reproduction Guide

<!-- Goal: someone starting from a clean environment can follow this top to bottom and reproduce every number in the README. Assume no prior context. -->

## Requirements

<!--
- **OS:** supported operating system(s) and versions
- **Language / runtime:** exact language version(s) and package manager (e.g. Python 3.11, Node 20, uv / pip / pnpm)
- **Key dependencies:** the handful of libraries/services that matter, with pinned versions if relevant
- **Hardware assumptions:** CPU/GPU/RAM/disk expectations; any cloud instance type; whether a GPU is required or optional
- **Credentials:** API keys or accounts needed, and which env vars hold them
-->

## Setup

<!-- Clone and install from scratch. Adjust commands to the actual toolchain. -->

```bash
# clone
git clone <repo-url>
cd <repo-dir>

# install
# <e.g. uv sync  /  pip install -r requirements.txt  /  pnpm install>

# configure
cp .env.example .env
# edit .env to add required keys
```

## Data

<!--
- **What's needed:** datasets, fixtures, or model artifacts required to run
- **Where it comes from:** download URL, script, or generation step; license/terms if relevant
- **Where it goes:** expected local path(s) and approximate size
- **Verification:** checksum or row count to confirm the data is correct
-->

## Running the baseline

<!-- Command(s) to run the baseline solution end to end. -->

```bash
# <command to run the baseline>
```

<!-- Expected output: paste a representative snippet of stdout / result file contents so the reader knows it worked. -->

```
<expected baseline output>
```

## Running the advanced solution

<!-- Command(s) to run the advanced solution end to end. -->

```bash
# <command to run the advanced solution>
```

<!-- Expected output: paste a representative snippet so the reader can confirm success. -->

```
<expected advanced output>
```

## Running the evaluation / benchmark

<!-- Command(s) to run the full evaluation that compares baseline vs advanced. -->

```bash
# <command to run the evaluation>
```

<!-- Expected output: the comparison table / summary the eval prints, showing baseline vs advanced on the headline metric(s). -->

```
<expected eval output: baseline vs advanced comparison>
```

## Cost & runtime

<!-- Fill in measured wall-clock time and monetary cost for each run type, plus the machine/config used. -->

| Run | Wall-clock time | Cost | Machine / config |
|---|---|---|---|
| Baseline run | <!-- --> | <!-- --> | <!-- --> |
| Advanced run | <!-- --> | <!-- --> | <!-- --> |
| Full eval | <!-- --> | <!-- --> | <!-- --> |

## Known environment gotchas

<!--
List the things that will trip someone up:
- platform-specific issues (Windows path handling, Apple Silicon wheels, etc.)
- version incompatibilities and the exact error they produce
- rate limits, quota, or nondeterminism in API calls
- flaky steps and how to retry them
- anything that must be run in a specific order
-->
