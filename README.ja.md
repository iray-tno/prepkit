# PrepKit

[English](README.md) | 日本語

競技プログラミングと機械学習のワークフローを効率化するPython製の総合ツール。AtCoder、Codingame、Kaggleなどのプラットフォーム向けに、コード管理、実験追跡、自動提出を支援します。

## 目次
- [インストール](#インストール)
  - [Python依存関係](#python依存関係)
  - [システム依存関係](#システム依存関係)
- [使い方](#使い方)
  - [C++プリプロセッサ](#cプリプロセッサ)
  - [C++ミニファイア](#cミニファイア)
  - [プロジェクト管理](#プロジェクト管理)
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
uv run prepkit cpp preprocess <file_path> [-I <include_path>]...
```

*   `<file_path>`: プリプロセスするメインC++ファイルのパス
*   `-I <include_path>` / `--include-path <include_path>`: オプション。インクルードファイルを検索する追加ディレクトリを指定。複数回使用可能

**例:**

```bash
uv run prepkit cpp preprocess my_project/main.cpp -I my_project/headers -I /usr/local/include
```

**重要**: `cpp preprocess`は**どこにあるC++ファイルでも単独で使用可能**です。`project new`で作成したプロジェクトである必要はありません。

```bash
# 既存のコードでも使える
cd ~/my_solution
uv run prepkit cpp preprocess solution.cpp -I .

# 出力をファイルに保存
uv run prepkit cpp preprocess main.cpp -I ./includes > submit.cpp
```

### C++ミニファイア

`cpp minify`コマンドは、C++ファイルから空白とコメントを積極的に削除し、厳しいコードサイズ制限のあるプラットフォームに適したものにします。

```bash
uv run prepkit cpp minify <file_path>
```

*   `<file_path>`: ミニファイするC++ファイルのパス

**例:**

```bash
uv run prepkit cpp minify my_solution.cpp
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
- コアC++プリプロセッサ機能の**4つの焦点を絞ったテスト**
- インクルード解決、constexpr置換、コメント削除、ミニファイのテスト
- **高速実行**（約1秒）で迅速な開発フィードバック

#### インテグレーションテスト (`tests/test_cpp_integration.py`)
- 実世界のシナリオをカバーする**13の包括的なテスト**
- リグレッションベースラインを使用した**スナップショットテスト**（リアルな競技プログラミングコード）
- **ビルド検証** - プリプロセスされたコードが`g++`でコンパイルできることを保証（最も重要）
- ロバスト性検証のための**プロパティベースドテスト**（Hypothesis使用）
- **パフォーマンスベンチマーク** - 処理速度の検証（典型的なファイルで約730ms）

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

**計画中:**
- **Rust**: 基本的なプリプロセッサとミニファイア（プラグイン構造は準備済み）
- **Kotlin**: 基本的なプリプロセッサとミニファイア（プラグイン構造は準備済み）

## 現在の状態と制限

### ✅ 完全実装済み
- **C++プリプロセッサ**: インクルード解決、整数constexpr置換、コメント削除
- **C++ミニファイア**: コンパイル互換性を保持したサイズ最適化出力
- **プロジェクトスキャフォールディング**: AtCoder、Codingame、Kaggle用のボイラープレート生成
- **包括的なテスト**: ビルド検証とパフォーマンスベンチマークを含む20のテスト

### ⚠️ 既知の制限
- **Constexprサポート**: 現在は整数リテラルに限定（浮動小数点、真偽値、複雑な式は未対応）
- **文字列Constexpr**: 文字列定数置換は未実装
- **Rust/Kotlinプラグイン**: プレースホルダー実装のみ

### 🔮 今後の機能強化
- 拡張constexprサポート（浮動小数点、真偽値、文字列リテラル）
- 完全なRustとKotlinプリプロセッサ実装
- 高度な最適化技術
- より多くの競技プログラミングプラットフォームとの統合

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
