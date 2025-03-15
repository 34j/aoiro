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

- 従来の仕訳帳には、次のような問題点がある。
  1. 外貨、証券、商品、固定資産の所持量が把握できない。
  2. 負数の忌避を行うため、各勘定科目の「ホームポジション」が貸方か借方か記入者が理解していなければならない。また、各ホームポジションごとに処理を分ける必要があり、実装が煩雑になる。
- 上記の問題を解決するため、本プロジェクトでは次のような手法を採用する。
  1. [Ellerman 1986](https://ellerman.org/Davids-Stuff/Maths/Omega-DEB.CV.pdf)によるVectorized Accountingを導入し、資産の種類ごとに取引量を記録する。
  2. 負数の忌避を行わず、仕訳帳の各行を「仕訳要素」の集合として表現する「一般化仕訳帳」を導入する。
- つまり、本システムは次の要素から構成される。
  - (日付の全体集合)`Date`: `Set`
  - (勘定科目の全体集合)`Account`: `Set`
  - (通貨の全体集合)`Currency`: `Set`
  - (「ホームポジション」が貸方か借方か)`is_debit`: `Account -> bool`
  - (決算で引き継ぐかどうか)`is_static`: `Account -> bool`
  - (一般化仕訳)`GeneralLedgerLine`: `Set<(Date, Account, Currency, Real)>`
  - (一般化仕訳帳)`GeneralLedger`: `Set<GeneralLedgerLine>`
- `GeneralLedger` さえあれば、賃借対照表・損益計算書の各項目までは、`groupby` + `sum` で計算できる。
- 各項目の集計と、齟齬がないことを確認するためには、勘定科目の5分類（資産、負債、純資産、収益、費用）の知識が必要である。本プロジェクトではこれに、EDINETタクソノミ、または青色申告決算書及び会計ソフトで一般的に使われる勘定科目に関するパッケージ[account-codes-jp](https://github.com/34j/account-codes-jp)を利用する。
- Vectorized Ledgerを通常の仕訳帳に変換するためには、各日付での資産の価値が必要である。本プロジェクトでは、現時点では外貨のみに対応している。（[みずほ銀行が提供する仲値](https://www.mizuhobank.co.jp/market/historical/index.html)をffillして利用する。）

- While it is often explained that the general ledger enables one to understand the accounting status at any given point in the history, but in reality, the real quantity of foreign currency, securities, goods, and fixed assets cannot be understood by the general ledger alone.
- This project aims to combine the "multidimensional" or "vectorized" accounting introduced by [Ellerman 1986](https://ellerman.org/Davids-Stuff/Maths/Omega-DEB.CV.pdf) and matrix accounting, and tries to create real-world blue-return accounting sheets by referring to [Ozawa 2023](https://waseda.repo.nii.ac.jp/record/77807/files/ShogakuKenkyukaKiyo_96_6.pdf).
- In short, this system is composed of the following elements:
  - `Date`: `Set`
  - `Account`: `Set`
  - `Currency`: `Set`
  - `is_debit`: `Account -> bool`
  - `is_static`: `Account -> bool`
  - `GeneralLedgerLine`: `Set<(Date, Account, Currency, Real)>`
  - `GeneralLedger`: `Set<GeneralLedgerLine>`
- `GeneralLedger` should be enough to create B/S, P/L sheets.

## Installation

Install this via pip (or your favourite package manager):

```shell
pip install aoiro
```

## Usage

- 本プロジェクトは主に仕入や株などの取引などを扱わない事業者向けに設計されているため、そうでない事業者にとっては、利用が困難な場合があります。その場合でも、Python APIを利用して、`sales`や`expenses`のようにカスタムリーダーを作成したり、一般化仕訳帳を手動で作成することで、対応が可能かもしれません。PRも歓迎します。

本プロジェクトでは、次のようなディレクトリ構造を利用する。

```shell
$ tree .
├── expenses
│   └── amazon.csv
├── general
│   └── bs.csv
└── sales
    ├── booth.csv
    ├── dlsite.csv
    └── steam.csv
```

1. 最も基本的な形式は`general`ディレクトリ内にある一般化仕訳帳を表すCSVファイル群であり、次のようなヘッダー**なし**CSVファイルである。

```csv
2025-01-01,現金,1000,売上,1000
2025-01-03,現金,10USD,現金,-1000
2025-01-02,消耗品,USD 8,現金,USD -10,土地,1 LandX
```

- 各行の順序は任意である。
- 第2行では両替を行っている。
- 第3行では、消耗品及び土地の購入を行っている。土地の相場は変化する可能性があるため、通貨`LandX`を導入する。
- 本プロジェクトはあくまで集計機としての立場（`groupby` + `sum`）をとり、「決算」の概念に直接対応していないため、昨年の賃借対照表を次のように入力する必要がある。例えば、次の例では、前期の期末時点で未入金の売掛金1000円、買掛金500円を繰り入れている。

```csv
2025-01-01,売掛金,1000,元入金,1000
2025-01-01,買掛金,500,元入金,-500
```

1. `expenses`は経費を表すCSVファイル群であり、次のようなヘッダー**あり**CSVファイルである。

```csv
発生日,勘定科目,金額
2025-01-01,消耗品費,1000
```

- 各行・各列の順序は任意である。

1. `sales`は売上を表すCSVファイル群であり、次のようなヘッダー**あり**CSVファイルである。

```csv
発生日,振込日,金額,源泉徴収,手数料
2024-12,2025-01-20,1234,true,100
```

- 各行・各列の順序は任意である。
- ファイル名は取引先を表す。
- 源泉徴収は`true`であれば一般的な源泉徴収額の計算を行うが、常に一致するとは限らない。具体的な数値に設定することもできる。

為替差損益は自動で計算され、最終的に次のような出力が得られる。

```shell
           amount currency debit_account credit_account
date
2024-01-01   1234                     現金            元入金
2024-01-20   1234                   事業主貸            売掛金
2024-01-20   1109                   事業主貸             諸口
2024-01-20    125           仮払税金(dlsite)             諸口
2024-01-20   1234                     諸口            売掛金
2024-01-31   1475                    売掛金      売上(steam)
2024-01-31   2345                    売掛金     売上(dlsite)
2024-02-20   2106                   事業主貸             諸口
2024-02-20    239           仮払税金(dlsite)             諸口
2024-02-20   2345                     諸口            売掛金
2024-02-20   1503                   事業主貸             諸口
2024-02-20   1475                     諸口            売掛金
2024-02-20     28                     諸口           為替差益
2024-03-01    765                   消耗品費           事業主借
╙── None/0
    ├─╼ 賃借対照表/3083
    │   ├─╼ 資産/5082
    │   │   ├─╼ 資産/-1234
    │   │   │   ├─╼ 現金/1234
    │   │   │   └─╼ 売掛金/-2468
    │   │   └─╼ 事業主貸/6316
    │   │       └─╼ 事業主貸/6316
    │   │           ├─╼ 事業主貸/5952
    │   │           └─╼ 仮払税金/364
    │   │               └─╼ 仮払税金(dlsite)/364
    │   ├─╼ 負債/765
    │   │   └─╼ 事業主借/765
    │   │       └─╼ 事業主借/765
    │   └─╼ 純資産/1234
    │       └─╼ 純資産/1234
    │           └─╼ 元入金/1234
    └─╼ 損益計算書/-3083
        ├─╼ 収益/3848
        │   └─╼ 売上/3848
        │       ├─╼ 売上/3820
        │       │   └─╼ 売上/3820
        │       │       ├─╼ 売上(steam)/1475
        │       │       └─╼ 売上(dlsite)/2345
        │       └─╼ 為替差益/28
        └─╼ 費用/765
            └─╼ 経費/765
                └─╼ 消耗品費/765
Sales per month
1: 3820
2: 0
3: 0
4: 0
5: 0
6: 0
7: 0
8: 0
9: 0
10: 0
11: 0
12: 0
```

仮払税金が想定される源泉徴収額であるが、実際には異なる場合があるため、支払調書を確認されたい。
上記の情報は、青色申告決算書を作成するにあたっては十分である。作成にあたっては、[国税庁 確定申告書等作成コーナー](https://www.keisan.nta.go.jp/kyoutu/ky/sm/top#bsctrl)が便利である。本プロジェクトでは、青色申告決算書の作成への対応は行わない。（あまりにも難しいため。大量の仕様書は[こちら](https://www.e-tax.nta.go.jp/shiyo/index.htm)。）

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
