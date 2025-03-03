# Aoiro

<p align="center">
  <a href="https://github.com/34j/aoiro/actions/workflows/ci.yml?query=branch%3Amain">
    <img src="https://img.shields.io/github/actions/workflow/status/34j/aoiro/ci.yml?branch=main&label=CI&logo=github&style=flat-square" alt="CI Status" >
  </a>
  <a href="https://aoiro.readthedocs.io">
    <img src="https://img.shields.io/readthedocs/aoiro.svg?logo=read-the-docs&logoColor=fff&style=flat-square" alt="Documentation Status">
  </a>
  <a href="https://codecov.io/gh/34j/aoiro">
    <img src="https://img.shields.io/codecov/c/github/34j/aoiro.svg?logo=codecov&logoColor=fff&style=flat-square" alt="Test coverage percentage">
  </a>
</p>
<p align="center">
  <a href="https://python-poetry.org/">
    <img src="https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json" alt="Poetry">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff">
  </a>
  <a href="https://github.com/pre-commit/pre-commit">
    <img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat-square" alt="pre-commit">
  </a>
</p>
<p align="center">
  <a href="https://pypi.org/project/aoiro/">
    <img src="https://img.shields.io/pypi/v/aoiro.svg?logo=python&logoColor=fff&style=flat-square" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/aoiro.svg?style=flat-square&logo=python&amp;logoColor=fff" alt="Supported Python versions">
  <img src="https://img.shields.io/pypi/l/aoiro.svg?style=flat-square" alt="License">
</p>

---

**Documentation**: <a href="https://aoiro.readthedocs.io" target="_blank">https://aoiro.readthedocs.io </a>

**Source Code**: <a href="https://github.com/34j/aoiro" target="_blank">https://github.com/34j/aoiro </a>

---

CSV-based 青色申告 CLI app

## Motivation

- While it is often explained that the general ledger enables one to understand the accounting status at any given point in the history, but in reality, the real quantity of foreign currency, securities, goods, and fixed assets cannot be understood by the general ledger alone.
- This project aims to combine the "multidimensional" or "vectorized" accounting introduced by [Ellerman 1986](https://ellerman.org/Davids-Stuff/Maths/Omega-DEB.CV.pdf) and matrix accounting, and tries to create real-world blue-return accounting sheets by referring to [Ozawa 2023](https://waseda.repo.nii.ac.jp/record/77807/files/ShogakuKenkyukaKiyo_96_6.pdf).
- In short, this system is composed of the following elements:
  - `Date`: `Set`
  - `Account`: `Set`
  - `Currency`: `Set`
  - `is_debit`: `Account -> bool`
  - `is_static`: `Account -> bool`
  - `LedgerLine`: `Set<(Date, Account, Currency, Real)>`
  - `Ledger`: `Set<LedgerLine>`
- `Ledger` should be enough to create B/S, P/L sheets.

## Installation

Install this via pip (or your favourite package manager):

`pip install aoiro`

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- prettier-ignore-start -->
<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/34j"><img src="https://avatars.githubusercontent.com/u/55338215?v=4?s=80" width="80px;" alt="34j"/><br /><sub><b>34j</b></sub></a><br /><a href="https://github.com/34j/aoiro/commits?author=34j" title="Code">💻</a> <a href="#ideas-34j" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/34j/aoiro/commits?author=34j" title="Documentation">📖</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
<!-- prettier-ignore-end -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

## Credits

This package was created with
[Copier](https://copier.readthedocs.io/) and the
[browniebroke/pypackage-template](https://github.com/browniebroke/pypackage-template)
project template.
