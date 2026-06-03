# PrepKit

[![Tests](https://github.com/iray-tno/prepkit/actions/workflows/test.yml/badge.svg)](https://github.com/iray-tno/prepkit/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

[English](README.md) | 日本語

競技プログラミングと機械学習のワークフローを効率化するPython製の総合ツール。AtCoder、Codingame、Kaggleなどのプラットフォーム向けに、コード管理、実験追跡、自動提出を支援します。

## 目次
- [インストール](#インストール)
  - [Python依存関係](#python依存関係)
  - [システム依存関係](#システム依存関係)
- [使い方](#使い方)
  - [C++プリプロセッサ](#cプリプロセッサ)
  - [C++ミニファイア](#cミニファイア)
  - [Rustプリプロセッサ](#rustプリプロセッサ)
  - [Rustミニファイア](#rustミニファイア)
  - [テストランナー](#テストランナー)
  - [プロジェクト管理](#プロジェクト管理)
  - [設定ファイル](#設定ファイル)
  - [Kaggle自動化](#kaggle自動化)
  - [実験管理](#実験管理)
- [テスト](#テスト)
- [プラグインアーキテクチャ](#プラグインアーキテクチャ)
- [コントリビューション](#コントリビューション)

## インストール

### Python依存関係

PrepKitは高速で信頼性の高い依存関係管理のため[uv](https://github.com/astral-sh/uv)を使用しています。

1.  **uvのインストール**（まだの場合）:
    ```bash
    # macOSとLinux
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # またはpipで
    pip install uv
    ```
2.  **プロジェクト依存関係のインストール**: プロジェクトルートで以下を実行:
    ```bash
    uv sync
    ```
    これにより仮想環境が作成され、必要なPythonパッケージが数秒でインストールされます。

### システム依存関係

PrepKitはC++の解析に`libclang`を、コードのフォーマットとミニファイに`clang-format`を使用します。

1.  **`libclang`のインストール**:
    *   **Debian/Ubuntu**:
        ```bash
        sudo apt-get update
        sudo apt-get install -y libclang-18 # または最新版（libclang-16, libclang-17など）
        ```
    *   **その他のLinuxディストリビューション**: お使いのディストリビューションのパッケージマネージャのドキュメントで正しい`libclang`パッケージ名を確認してください。

2.  **`clang-format`のインストール**:
    *   **Debian/Ubuntu**:
        ```bash
        sudo apt-get update
        sudo apt-get install -y clang-format
        ```
    *   **その他のLinuxディストリビューション**: お使いのディストリビューションのパッケージマネージャのドキュメントで正しい`clang-format`パッケージ名を確認してください。

### WSL対応

PrepKitは**WSL (Windows Subsystem for Linux)で完全に動作します**。WSL2のUbuntuまたはDebianで上記のインストール手順を実行してください。Windowsファイルシステム（`/mnt/c/`、`/mnt/e/`など）からのファイルアクセスも可能です。

## 使い方

すべてのコマンドは`uv run prepkit <command>`で実行します。

### C++プリプロセッサ

`cpp preprocess`コマンドは、複数のC++ファイルを1つのファイルに統合し、`constexpr`変数を値に置換し、コメントを削除し、コードをフォーマットします。

```bash
uv run prepkit cpp preprocess <file_path> [-I <include_path>]... [-D <NAME=VALUE>]... [-o <output_file>]
```

*   `<file_path>`: プリプロセスするメインC++ファイルのパス
*   `-I <include_path>` / `--include-path <include_path>`: オプション。インクルードファイルを検索する追加ディレクトリを指定。複数回使用可能
*   `-D <NAME=VALUE>` / `--define <NAME=VALUE>`: オプション。チューニング可能なパラメータ値を注入（下記のチューニング可能パラメータセクション参照）。複数回使用可能
*   `-o <output_file>` / `--output <output_file>`: オプション。標準出力ではなくファイルに出力

**例:**

```bash
# 標準出力に出力
uv run prepkit cpp preprocess my_project/main.cpp -I my_project/headers

# ファイルに書き込み
uv run prepkit cpp preprocess my_project/main.cpp -I my_project/headers -o preprocessed.cpp

# チューニング可能パラメータを注入
uv run prepkit cpp preprocess solution.cpp -D TEMP_START=1500.0 -D BEAM_WIDTH=100
```

**重要**: `cpp preprocess`は**どこにあるC++ファイルでも単独で使用可能**です。`project new`で作成したプロジェクトである必要はありません。

```bash
# 既存のコードでも使える
cd ~/my_solution
uv run prepkit cpp preprocess solution.cpp -I .

# 出力をファイルに保存
uv run prepkit cpp preprocess main.cpp -I ./includes > submit.cpp
```

#### ハイパーパラメータ最適化のためのチューニング可能パラメータ

PrepKitは、競技プログラミングと機械学習ワークフロー向けの**チューニング可能パラメータ注入**をサポートしています。この機能は、ヒューリスティック/マラソンコンテストでの**Optuna最適化**と**WandB実験トラッキング**のために設計されています。

**仕組み:**

1. ソースコードで最適化したいパラメータに `// @tune` コメントでマーク
2. CLIフラグ（`-D`）、設定ファイル、またはPython APIで異なる値を注入
3. 注入前のソースコードはデフォルト値で有効なまま

**例 (C++):**

```cpp
// source.cpp
constexpr double TEMP_START = 1000.0;  // @tune
constexpr int BEAM_WIDTH = 50;         // @tune
constexpr int MAX_TURNS = 100;         // 固定パラメータ（マークなし）

int main() {
    // これらのパラメータを使用するアルゴリズム
    return 0;
}
```

**CLIで注入:**

```bash
# 異なるパラメータ値をテスト
uv run prepkit cpp preprocess source.cpp -D TEMP_START=1500.0 -D BEAM_WIDTH=75

# マークされたパラメータのみ置換される。MAX_TURNSは100のまま
```

**Python APIで注入 (Optuna用):**

```python
from plugins.cpp_plugin import CppPreprocessor

preprocessor = CppPreprocessor()

# Optunaの目的関数内で
def objective(trial):
    temp_start = trial.suggest_float("TEMP_START", 800.0, 2000.0)
    beam_width = trial.suggest_int("BEAM_WIDTH", 20, 100)

    # トライアルパラメータを注入
    code = preprocessor.preprocess(
        "solution.cpp", [],
        defines={
            "TEMP_START": str(temp_start),
            "BEAM_WIDTH": str(beam_width)
        }
    )

    # 注入されたパラメータでコンパイルして実行
    # ... スコアを評価 ...
    return score
```

**設定ファイルで注入:**

```yaml
# prepkit_config.yaml
cpp_preprocess:
  defines:
    TEMP_START: "1500.0"
    BEAM_WIDTH: "75"
```

**主な機能:**

- `// @tune` でマークされたパラメータのみが置換可能
- デフォルト値を持つソースコードは有効でコンパイル可能なまま
- すべての `constexpr` 型をサポート: `int`, `float`, `double`, `bool`
- OptunaトライアルとWandB実験とシームレスに連携
- 設定値はCLIフラグで上書き可能

### C++ミニファイア

`cpp minify`コマンドは、C++ファイルから空白とコメントを積極的に削除し、厳しいコードサイズ制限のあるプラットフォームに適したものにします。

```bash
uv run prepkit cpp minify <file_path> [-o <output_file>]
```

*   `<file_path>`: ミニファイするC++ファイルのパス
*   `-o <output_file>` / `--output <output_file>`: オプション。標準出力ではなくファイルに出力

**例:**

```bash
# 標準出力に出力
uv run prepkit cpp minify my_solution.cpp

# ファイルに書き込み
uv run prepkit cpp minify my_solution.cpp -o minified.cpp
```

### Rustプリプロセッサ

`rust preprocess`コマンドは、複数ファイルのRustプロジェクトを1つのファイルにまとめます。各`mod name;`宣言をインラインの`mod name { ... }`ブロックで**ラップ**することでフラット化するため、各モジュールの名前空間が保たれます。これにより、異なるモジュールで同名の項目が衝突せず、元のパスもすべてそのまま解決されます。シングルファイル提出が必要な競技プログラミングプラットフォームに最適です。

```bash
uv run prepkit rust preprocess <file_path> [-I <include_path>]... [-D <NAME=VALUE>]... [-o <output_file>]
```

*   `<file_path>`: プリプロセスするメインRustファイル（main.rsまたはlib.rs）のパス
*   `-I <include_path>` / `--include-path <include_path>`: オプション。モジュールを検索する追加ディレクトリを指定。複数回使用可能
*   `-D <NAME=VALUE>` / `--define <NAME=VALUE>`: オプション。チューニング可能なパラメータ値を注入（下記のRust向けチューニング可能パラメータセクション参照）。複数回使用可能
*   `-o <output_file>` / `--output <output_file>`: オプション。標準出力ではなくファイルに出力

**特徴:**

- **モジュールのラップ**: `mod name;`宣言を解決し、各モジュールの内容を再帰的に`mod name { ... }`でラップして名前空間を保持
- **名前衝突なし**: モジュール間で同名の項目も分離されたまま。元のパス（`crate::a::b`、`std::collections::HashMap`、`Type::method`）もそのまま解決
- **カスタムパス**: `#[path = "..."]`属性によるカスタムモジュール位置に対応
- **条件付きコンパイル**: プラットフォーム固有コードのための`#[cfg(...)]`属性を保持
- **glob / use インポート**: `use module::*;`などの`use`文をそのまま維持
- **インラインモジュール**: インラインの`mod name { ... }`宣言を保持
- **マクロの保持**: `macro_rules!`や手続き的マクロをそのまま維持
- **自動フォーマット**: `rustfmt`が利用可能であればクリーンな出力に整形

**例:**

```bash
# 標準出力に出力
uv run prepkit rust preprocess my_project/main.rs -I my_project/modules

# ファイルに書き込み
uv run prepkit rust preprocess my_project/main.rs -I my_project/modules -o submission.rs
```

**入力例（複数ファイルのプロジェクト）:**

```rust
// main.rs
mod utils;

fn main() {
    let result = utils::add(5, 3);
    println!("Result: {}", result);
}

// utils.rs
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

**出力（単一ファイル）:**

```rust
mod utils {
    pub fn add(a: i32, b: i32) -> i32 {
        a + b
    }
}

fn main() {
    let result = utils::add(5, 3);
    println!("Result: {}", result);
}
```

#### Rust向けのチューニング可能パラメータ

C++プリプロセッサと同様に、Rustプリプロセッサもハイパーパラメータ最適化向けの**チューニング可能パラメータ注入**をサポートします。

**例 (Rust):**

```rust
// solution.rs
const TEMP_START: f64 = 1000.0;  // @tune
const BEAM_WIDTH: i32 = 50;      // @tune
const MAX_TURNS: i32 = 100;      // 固定パラメータ（マークなし）

fn main() {
    // これらのパラメータを使用するアルゴリズム
}
```

**CLIで注入:**

```bash
# 異なるパラメータ値をテスト
uv run prepkit rust preprocess solution.rs -D TEMP_START=1500.0 -D BEAM_WIDTH=75

# マークされたパラメータのみ置換される。MAX_TURNSは100のまま
```

**Python APIで注入 (Optuna用):**

```python
from plugins.rust_plugin import RustPreprocessor

preprocessor = RustPreprocessor()

# Optunaの目的関数内で
def objective(trial):
    temp_start = trial.suggest_float("TEMP_START", 800.0, 2000.0)
    beam_width = trial.suggest_int("BEAM_WIDTH", 20, 100)

    # トライアルパラメータを注入
    code = preprocessor.preprocess(
        "solution.rs", [],
        defines={
            "TEMP_START": str(temp_start),
            "BEAM_WIDTH": str(beam_width)
        }
    )

    # 注入されたパラメータでコンパイルして実行
    # ... スコアを評価 ...
    return score
```

**設定ファイルで注入:**

```yaml
# prepkit_config.yaml
rust_preprocess:
  defines:
    TEMP_START: "1500.0"
    BEAM_WIDTH: "75"
```

**主な機能:**

- C++と同じマーカーベースの仕組み（`// @tune`）
- マークされたパラメータのみが置換される
- デフォルト値を持つソースコードは有効なRustのまま
- すべての`const`型をサポート: `i32`, `f64`, `bool`など
- モジュールのラップと併用可能（どのモジュールのパラメータもチューニング可能）

### Rustミニファイア

`rust minify`コマンドは、Rustファイルからコメントと余分な空白を削除し、コードサイズを削減します。

```bash
uv run prepkit rust minify <file_path> [-o <output_file>]
```

*   `<file_path>`: ミニファイするRustファイルのパス
*   `-o <output_file>` / `--output <output_file>`: オプション。標準出力ではなくファイルに出力

**例:**

```bash
# 標準出力に出力
uv run prepkit rust minify my_solution.rs

# ファイルに書き込み
uv run prepkit rust minify my_solution.rs -o minified.rs
```

### テストランナー

`test`コマンドは、C++またはRustコードをコンパイルして実行し、オプションでテスト入力/出力の比較を行います。競技プログラミングの練習と検証に最適です。言語はファイル拡張子（.cpp, .rs）から自動検出されます。

```bash
uv run prepkit test <file_path> [-i <input_file>] [-e <expected_file>] [--preprocess] [-I <include_path>]... [--rust]
```

*   `<file_path>`: コンパイルして実行するソースファイルのパス（C++またはRust）
*   `-i <input_file>` / `--input <input_file>`: オプション。プログラムに標準入力として渡す入力ファイル
*   `-e <expected_file>` / `--expected <expected_file>`: オプション。検証用の期待される出力ファイル
*   `--preprocess`: オプション。コンパイル前にファイルをプリプロセス（インクルード/モジュールを解決し、定数をインライン化）
*   `-I <include_path>` / `--include-path <include_path>`: オプション。プリプロセス用のインクルードパス（`--preprocess`使用時のみ）
*   `--rust`: オプション。Rustモードを強制（`.rs`拡張子からは自動検出）

**C++の例:**

```bash
# 基本的なコンパイルと実行
uv run prepkit test solution.cpp

# テスト入力あり
uv run prepkit test solution.cpp -i input.txt

# 入力と期待される出力の検証
uv run prepkit test solution.cpp -i input.txt -e expected.txt

# プリプロセスしてからテスト
uv run prepkit test solution.cpp --preprocess -I ./lib -i input.txt -e expected.txt
```

**Rustの例:**

```bash
# 基本的なコンパイルと実行（.rs拡張子を自動検出）
uv run prepkit test solution.rs

# テスト入力と出力の検証
uv run prepkit test solution.rs -i input.txt -e expected.txt

# 複数ファイルのプロジェクトをプリプロセスしてからテスト
uv run prepkit test main.rs --preprocess -I ./modules -i input.txt -e expected.txt

# .rs以外のファイルでRustモードを強制
uv run prepkit test solution.rust --rust
```

**仕組み:**

1. ファイル拡張子から**言語を自動検出**（.cpp, .cc, .cxx, .c++ → C++; .rs → Rust）
2. `g++`または`rustc`でコードを**コンパイル**（`prepkit_config.yaml`で設定可能）
3. オプションの入力ファイルで実行ファイルを**実行**
4. 提供された場合、出力を期待される結果と**比較**
5. 明確なエラーメッセージで成功または失敗を**報告**

**設定:**

`prepkit_config.yaml`でコンパイラ設定を指定できます:

```yaml
# C++コンパイル設定
cpp_compile:
  std: "c++17"           # C++標準
  flags: ["-O2", "-Wall"] # 追加フラグ

# Rustコンパイル設定
rust_compile:
  edition: "2021"        # Rustエディション
  flags: ["-C", "opt-level=2"]  # 追加フラグ

# テスト設定（両言語に適用）
test:
  timeout: 5             # 実行タイムアウト（秒）
  input_file: "input.txt"      # デフォルトの入力ファイル
  expected_file: "expected.txt" # デフォルトの期待される出力
```

### プロジェクト管理

PrepKitは、異なる競技プログラミングプラットフォーム向けのボイラープレートコードを素早く作成するプロジェクトスキャフォールディングを提供します。

#### 新規プロジェクトの作成

```bash
uv run prepkit project new <project_name> [--lang <language>] [--type <project_type>]
```

*   `<project_name>`: 作成するプロジェクトディレクトリの名前
*   `--lang <language>`: プログラミング言語（デフォルト: `cpp`）
*   `--type <project_type>`: プロジェクトテンプレートタイプ（デフォルト: `atcoder-algorithm`）

**利用可能なプロジェクトタイプ:**
- `atcoder-algorithm`: AtCoder競技プログラミング用セットアップ（**AHC推奨**）
- `codingame`: Codingame用セットアップ（ミニファイ有効）
- `kaggle`: Kaggleコンペティション用セットアップ

**例:**

```bash
# AHC用プロジェクト
uv run prepkit project new ahc042 --lang cpp --type atcoder-algorithm

# デフォルト設定でプロジェクト作成
uv run prepkit project new abc123
```

これにより、ボイラープレートコードと指定プラットフォーム用に設定された`prepkit_config.yaml`ファイルを含む新しいディレクトリが作成されます。

### 設定ファイル

PrepKitは、プロジェクトディレクトリの`prepkit_config.yaml`を通じたプロジェクトレベルの設定をサポートしています。これにより、コマンドのデフォルト値を設定し、繰り返しのコマンドラインフラグを避けることができます。

#### 設定構造

```yaml
project_type: atcoder-algorithm

cpp_preprocess:
  include_paths:
    - ./lib
    - ./includes
  minify_output: false

cpp_compile:
  std: c++20
  flags:
    - "-O2"
    - "-Wall"

test:
  timeout: 10
  input_file: input.txt
  expected_file: expected.txt
```

#### 設定オプション

**`cpp_preprocess`**: `cpp preprocess`コマンドのデフォルト設定
- `include_paths`: インクルードファイルを検索するディレクトリのリスト（`-I`フラグと同等）
- `minify_output`: プリプロセスされた出力をミニファイするかどうか

**`cpp_compile`**: `test`コマンドで使用されるコンパイラ設定
- `std`: C++標準（例: `c++11`, `c++17`, `c++20`）
- `flags`: 追加のコンパイラフラグ（例: `-O2`, `-Wall`）

**`test`**: `test`コマンドのデフォルト設定
- `timeout`: 最大実行時間（秒）（デフォルト: 5）
- `input_file`: デフォルトの入力ファイルパス
- `expected_file`: デフォルトの期待される出力ファイルパス

#### CLIオーバーライド

コマンドラインフラグは常に設定ファイルの値よりも優先されます。例:

```bash
# 設定で./libをインクルードパスとして指定
# このコマンドは./extraを検索パスに追加
uv run prepkit cpp preprocess main.cpp -I ./extra
# 結果: ./lib（設定から）と./extra（CLIから）の両方を検索
```

### Kaggle自動化

PrepKitは一般的なKaggleワークフローを自動化するコマンドを提供します。

#### ノートブックのプッシュ

JupyterノートブックまたはPythonスクリプトをKaggle Kernelsにプッシュします。

```bash
uv run prepkit kaggle push-notebook <notebook_file> [--title <title>] [--slug <slug>] [--language <language>] [--private|--public]
```

*   `<notebook_file>`: `.ipynb`または`.py`ファイルのパス
*   `--title`: オプション。Kaggleノートブックのタイトル。デフォルトはファイル名から派生
*   `--slug`: オプション。Kaggleノートブックのスラッグ。デフォルトはタイトルから派生
*   `--language`: オプション。ノートブックのプログラミング言語（デフォルト: `python`）
*   `--private` / `--public`: オプション。ノートブックの可視性を設定（デフォルト: `private`）

**重要:** このコマンドを実行後、ノートブックのディレクトリに`kernel-metadata.json`ファイルが生成されます。最初のプッシュが成功する前に、このJSONファイルの`id`フィールドの`<KAGGLE_USERNAME>`を実際のKaggleユーザー名に**手動で置換する必要があります**。

**例:**

```bash
uv run prepkit kaggle push-notebook my_notebook.ipynb --title "My Kaggle Analysis" --public
```

#### コンペティション提出

予測ファイルをKaggleコンペティションに提出します。

```bash
uv run prepkit kaggle submit-competition <submission_file> --competition <competition_name> [--message <message>]
```

*   `<submission_file>`: 提出するCSVまたはその他の必要なファイルのパス
*   `--competition <competition_name>`: **必須**。KaggleコンペティションのURLスラッグ（例: `titanic`）
*   `--message <message>`: オプション。提出のメッセージ（デフォルト: `From PrepKit`）

**例:**

```bash
uv run prepkit kaggle submit-competition submission.csv --competition titanic --message "First submission with new model"
```

### 実験管理

PrepKitは、構造化された実験設定、ハイパーパラメータ最適化、追跡のためにHydra、Optuna、Weights & Biases (WandB)と統合しています。

#### 実験の実行

Hydra設定ファイルに基づいて実験を実行します。

```bash
uv run prepkit experiment run <config_path> <config_name>
```

*   `<config_path>`: Hydra設定ディレクトリのパス（プロジェクトルートからの相対パス）
*   `<config_name>`: メイン設定ファイルの名前（例: `config.yaml`）

**例:**

`conf/config.yaml`がある場合:

```yaml
# conf/config.yaml
params:
  learning_rate: 0.01
  epochs: 10
wandb:
  project: my_ml_project
  entity: your_wandb_entity
```

実験を実行:

```bash
uv run prepkit experiment run conf config
```

コマンドラインからパラメータをオーバーライド可能:

```bash
uv run prepkit experiment run conf config params.learning_rate=0.005
```

#### ハイパーパラメータの最適化

Optunaを使用してハイパーパラメータ最適化を実行し、結果をWandBで追跡します。

```bash
uv run prepkit experiment optimize <config_path> <config_name>
```

*   `<config_path>`: Hydra設定ディレクトリのパス（プロジェクトルートからの相対パス）。この設定はOptunaの探索空間を定義する必要があります
*   `<config_name>`: メイン設定ファイルの名前

**例:**

探索空間を定義する`conf/optuna_config.yaml`がある場合:

```yaml
# conf/optuna_config.yaml
# Optuna探索空間の例
params:
  learning_rate: ??? # Optunaで最適化
  epochs: 10
wandb:
  project: my_ml_project_optuna
  entity: your_wandb_entity
```

最適化を実行:

```bash
uv run prepkit experiment optimize conf optuna_config hydra.sweeper.sampler.seed=42
```

## テスト

PrepKitは信頼性と正確性を保証するための複数のテスト戦略を含む包括的なテストスイートを備えています。

### テストの実行

**すべてのテストを実行:**
```bash
uv run pytest
```

**特定のテストカテゴリを実行:**
```bash
# ユニットテストのみ
uv run pytest tests/test_cpp_preprocessor.py

# インテグレーションテストのみ
uv run pytest tests/test_cpp_integration.py

# ビルド検証テスト（g++が必要）
uv run pytest -m build

# パフォーマンスベンチマーク
uv run pytest --benchmark-only
```

### テスト構造

#### ユニットテスト (`tests/test_cpp_preprocessor.py`)
- コアC++プリプロセッサ機能の**7つの焦点を絞ったテスト**
- インクルード解決、constexpr置換（int、float、bool、string）、コメント削除、ミニファイのテスト
- **高速実行**（約1秒）で迅速な開発フィードバック

#### インテグレーションテスト (`tests/test_cpp_integration.py`)
- 実世界のシナリオをカバーする**13の包括的なテスト**
- リグレッションベースラインを使用した**スナップショットテスト**（リアルな競技プログラミングコード）
- **ビルド検証** - プリプロセスされたコードが`g++`でコンパイルできることを保証（最も重要）
- ロバスト性検証のための**プロパティベースドテスト**（Hypothesis使用）
- **パフォーマンスベンチマーク** - 処理速度の検証（典型的なファイルで約750ms）

#### CLIテスト (`tests/test_cli.py`)
- コマンドラインインターフェース機能の**17のテスト**
- 設定ファイルの読み込みと検証
- 各種オプション付きテストランナー（入力、期待される出力、プリプロセス）
- cppコマンドの出力フラグ（`-o/--output`）
- バージョンフラグの検証

#### エラーハンドリングテスト (`tests/test_error_messages.py`)
- エラーメッセージとエッジケースを検証する**9のテスト**
- 役立つヒント付きのインクルードファイル不在エラーメッセージ
- 循環依存検出
- コンパイルエラーハンドリング
- constexpr置換における文字列リテラル保護

#### テストカテゴリ
- **スナップショットテスト**: ゴールデンマスターファイルを使用したリグレッションテスト
- **ビルド検証**: 複数のコンパイラフラグでのコンパイルテスト
- **プロパティベースド**: Hypothesisを使用したランダム入力でのファズテスト
- **パフォーマンス**: `pytest-benchmark`でのベンチマーク
- **エラーハンドリング**: エッジケースと失敗モードのテスト

### テスト依存関係

テストスイートには高度なテストライブラリが含まれます:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4,<8.0",
    "syrupy>=4.6.0,<5.0",      # スナップショットテスト
    "hypothesis>=6.0.0,<7.0",  # プロパティベースドテスト
    "pytest-xdist>=3.0.0,<4.0", # 並列実行
    "pytest-benchmark>=4.0.0,<5.0" # パフォーマンステスト
]
```

### テストデータ

リアルなテストケースを含む:
- **アルゴリズムテンプレート**: セグメント木実装
- **競技プログラミング例**: 完全なAtCoder/Codingameソリューション
- **インクルードシナリオ**: 多階層ヘッダー依存関係
- **Constexpr例**: 複雑な定数宣言

## プラグインアーキテクチャ

PrepKitはプラグインベースのアーキテクチャで設計されており、新しいプログラミング言語や機能を簡単に拡張できます。

プラグインはPythonの`entry_points`メカニズムで検出されます。異なる言語用の新しいプリプロセッサやミニファイアは、`BasePreprocessor`または`BaseMinifier`（`src/base_interfaces.py`で定義）を継承するPythonクラスを作成し、`pyproject.toml`の`[project.entry-points."prepkit.preprocessors"]`または`[project.entry-points."prepkit.minifiers"]`セクションに登録することで追加できます。

### 現在のプラグインサポート

**実装済み:**
- **C++**: libclang統合による完全なプリプロセッサとミニファイア
  - ローカルヘッダーのインクルード解決
  - Constexpr置換（整数リテラル）
  - コメント削除とコードミニファイ
  - g++でのビルド検証

- **Rust**: モジュールのラップによるプリプロセッサとミニファイア
  - `mod name;`の再帰的な解決と`mod name { ... }`へのラップ
  - チューニング可能パラメータ注入、カスタムパス、条件付きコンパイル
  - rustcでのビルド検証

**計画中:**
- **Kotlin**: 基本的なプリプロセッサとミニファイア（プラグイン構造は準備済み）

## 現在の状態と制限

### ✅ 完全実装済み
- **C++プリプロセッサ**: インクルード解決、チューニング可能パラメータ注入、コメント削除
- **C++ミニファイア**: コンパイル互換性を保持したサイズ最適化出力
- **Rustプリプロセッサ**: モジュールフラット化、チューニング可能パラメータ注入、カスタムパス、条件付きコンパイルのサポート
- **Rustミニファイア**: コメント削除と空白圧縮
- **チューニング可能パラメータ**: Optuna/WandB最適化ワークフロー向けのマーカーベースのハイパーパラメータ注入
- **テストランナー**: C++（g++）とRust（rustc）の両方でコンパイル、実行、出力検証（前処理サポート付き）
- **設定システム**: `prepkit_config.yaml`によるプロジェクトレベルのデフォルト
- **プロジェクトスキャフォールディング**: AtCoder、Codingame、Kaggle用のボイラープレート生成
- **包括的なテスト**: CLI、統合、エラーハンドリング、ビルド検証を含む113のテスト

### ⚠️ 既知の制限
- **Constexpr/Const（C++/Rust）**: 設計上、式は評価しません。チューニング可能パラメータには `// @tune` マーカー付きのリテラル値を使用するか、複雑な式はシングルファイルコンパイル用にそのまま残してください。
- **Kotlinプラグイン**: プレースホルダー実装のみ

### 🔮 今後の機能強化
- 完全なKotlinプリプロセッサ実装
- 高度な最適化技術（コードサイズ、パフォーマンス）
- より多くの競技プログラミングプラットフォームとの統合
- 追加の実験トラッキング統合

## AHC（AtCoder Heuristic Contest）での使い方

### 典型的なワークフロー

```bash
# 1. 新規コンテスト用プロジェクト作成
uv run prepkit project new ahc042 --type atcoder-algorithm
cd ahc042

# 2. コード開発（複数ファイルに分けて書く）
# main.cpp - メインロジック
# includes/data_structures.hpp - データ構造
# includes/algorithms.hpp - アルゴリズム

# 3. 提出用に1ファイルにまとめる
uv run prepkit cpp preprocess main.cpp -I ./includes > submit.cpp

# 4. 動作確認
g++ -std=c++20 -O2 submit.cpp -o solution
./solution < input.txt

# 5. submit.cppをAtCoderに提出
```

### プロジェクトなしで使う場合

```bash
# 既存のコードベースで直接使用
cd ~/my_ahc_solution
uv run prepkit cpp preprocess solution.cpp -I . > submit.cpp
```

## 開発ガイド

### 実践的な使用

PrepKitは自身の開発中にも使用されるように設計されています。詳細は[DOGFOODING.md](DOGFOODING.md)を参照:

- **実際の競技プログラミング練習との統合**
- **AIアシスタントワークフローの最適化**
- **日常的な開発ルーチン**
- **実際の使用を通じたパフォーマンス監視**

### テスト戦略

包括的なテストワークフローについては[TESTING.md](TESTING.md)を参照:

- **多層テストアプローチ**（ユニット、インテグレーション、ビルド検証）
- **パフォーマンスベンチマーク**とリグレッション検出
- **テスト駆動開発**パターン
- **継続的インテグレーション**のベストプラクティス

## コントリビューション

コントリビューションを歓迎します！詳細なアーキテクチャの決定と今後のロードマップについては、開発計画（`競技プログラミング支援ツール開発計画.md`）を参照してください。

### 開発セットアップ

1. **リポジトリのクローン**
2. **依存関係のインストール**: `uv sync`
3. **システム依存関係のインストール**: `libclang-18`と`clang-format`
4. **テストの実行**: `uv run pytest`
5. **ビルド検証の確認**: `uv run pytest -m build`

### プルリクエストガイドライン

- ビルド検証テストを含むすべてのテストが通ることを確認
- 新機能には適切なテストカバレッジを追加
- ユーザー向けの変更についてはドキュメントを更新
- 既存のコードスタイルとパターンに従う
