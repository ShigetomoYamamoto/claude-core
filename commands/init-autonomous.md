---
name: 自律開発基盤セットアップ
description: |
  新プロジェクトに AI エージェント自走のための環境基盤を一括生成します。
  スタック自動検出 → 情報収集 → ツール整備 → CLAUDE.md / .claude / docs / .github を生成
---

# /init-autonomous — 自律開発基盤セットアップ

このコマンドは任意のプロジェクトディレクトリで実行すると、AIエージェントが自走して開発を完成させるための環境基盤を一括生成します。

**解決する問題:**
1. **止まる** → 確認が必要・仕様が曖昧
2. **間違える** → 判断基準がない・設計意図がわからない
3. **壊れたまま進む** → 品質チェックが自動化されていない

---

## ステップ 1: 既存ファイルからスタックを自動検出

カレントディレクトリで以下のファイルを順に確認し、技術スタックを特定する。

**検出ルール:**
- `composer.json` が存在 → PHP を確認。`laravel/framework` 依存があれば Laravel
- `package.json` が存在 → Node.js 系。`dependencies` / `devDependencies` を読んで特定:
  - `next` → Next.js（`appDir` 設定があれば App Router、なければ Pages Router）
  - `nuxt` → Nuxt
  - `react` のみ → React（CRA / Vite / etc）
  - `vue` のみ → Vue
  - `express` / `fastify` / `hono` → Node.js バックエンド
- `requirements.txt` または `pyproject.toml` が存在 → Python。内容を確認:
  - `django` → Django
  - `fastapi` → FastAPI
  - `flask` → Flask
- `go.mod` が存在 → Go
- `Cargo.toml` が存在 → Rust
- `build.gradle` または `pom.xml` が存在 → Java/Kotlin

複数検出した場合はフロントエンド・バックエンドに分けて認識する（例: Next.js + Laravel）。

**スタック検出変数として以下を内部で保持する（以降のステップで参照）:**
- `STACK_FRONTEND`: 検出結果（例: `nextjs`, `react`, `vue`, `nuxt`, なし）
- `STACK_BACKEND`: 検出結果（例: `laravel`, `django`, `fastapi`, `express`, `go`, `rust`, なし）
- `USES_TYPESCRIPT`: `tsconfig.json` が存在するか、または package.json に `typescript` があれば `true`
- `TEST_FRAMEWORK`: 後述の情報収集で決定

何も検出できない場合はステップ 2 の質問 0 として「使用技術スタックを教えてください」を先頭に追加する。

---

## ステップ 2: 最小限の情報収集（最大5問）

ファイルから推測できた項目は省略してよい。質問はまとめて一度に提示し、ユーザーの回答を待つ。

**質問リスト（該当するものだけ聞く）:**

1. **プロジェクト名と一行説明**（例: `recipe-cost` — 飲食店向けレシピ原価管理ツール）
   - `package.json` の `name` / `description` や `composer.json` から推測できる場合は省略し、推測値を提示して確認のみ行う

2. **主要ドメインエンティティ 3〜5個**（例: ユーザー・商品・注文・在庫）
   - DBマイグレーションファイルやモデルディレクトリが存在する場合は既存ファイル名から推測して提示する

3. **ユーザーロール構成**（例: `admin / editor / viewer`。認証なしなら「なし」）
   - ミドルウェアや Policy ファイルから推測できる場合は提示する

4. **テストフレームワーク**（未確定なら推奨を提示して確認）
   - Laravel → Pest を推奨
   - Next.js / React → Vitest を推奨
   - Python → pytest を推奨
   - Go → 標準 `testing` パッケージ + testify を推奨

5. **特に避けたいライブラリや制約**（なければスキップ）

6. **既存の仕様書・設計書**（なければスキップ）
   - 既存資料がある場合はファイルパスを教えてください
   - 例: `仕様書: docs/spec.md、設計書: docs/architecture.md`
   - 複数ある場合はすべて列挙してください

収集した情報を以下の変数として保持する（以降のステップで参照）:
- `PROJECT_NAME`: プロジェクト名（スラッグ形式）
- `PROJECT_DESCRIPTION`: 一行説明
- `DOMAIN_ENTITIES`: エンティティリスト
- `USER_ROLES`: ロール構成（なければ「認証なし」）
- `TEST_FRAMEWORK`: 確定したテストフレームワーク
- `CONSTRAINTS`: 制約事項（なければ空）
- `EXISTING_DOCS`: 既存資料のパスと内容の種別（なければ空）

---

## ステップ 3: ツール・環境の整備

検出したスタックに基づき、プロジェクトに必要なツールを特定する。次に、マシン上の導入状況を確認し、**未導入のものだけ**を導入または案内する。

### 3-A: 必要なツールの特定

スタックに応じて以下のリストを構築する:

**共通（全スタック）:**
- `git`
- `gh`（GitHub CLI）

**PHP/Laravel 検出時:**
- `php` 8.2 以上、`composer`
- `./vendor/bin/pint`・`./vendor/bin/pest`（`composer install` で自動導入）

**Node.js 系検出時:**
- `node` 20 以上
- パッケージマネージャー（`package.json` の `packageManager` フィールドで判定: `npm` / `pnpm` / `yarn`）
- `eslint`・`prettier`・テストフレームワーク（`TEST_FRAMEWORK` 変数を参照）

**TypeScript 検出時:** `typescript`

**Python 検出時:** `python` 3.11 以上、`pip`・`ruff`・`pytest`・`pytest-cov`

**Claude Code — MCP（スタック別）:**

| 条件 | 追加する MCP |
|-----|------------|
| `.github/` を生成する（ほぼ常時） | GitHub MCP |
| `playwright` が依存にある | Playwright MCP |
| `@supabase/` が依存にある | Supabase MCP |
| `vercel.json` または Vercel 関連ファイルがある | Vercel MCP |

**Claude Code — Plugins（スタック別）:**

| 条件 | 案内する Plugin |
|-----|--------------|
| `@supabase/` が依存にある | Supabase Plugin |
| `vercel.json` または Vercel 関連ファイルがある | Vercel Plugin |
| 環境変数に `SLACK_` が含まれる | Slack Plugin |

**Claude Code — Skills（スタック別）:**

ステップ 4 の `.claude/commands/` 生成に加え、スタック別の既存 Skills を案内する:

| 条件 | 案内する Skill |
|-----|-------------|
| Vercel 関連ファイルがある | `vercel:deploy`・`vercel:env`・`vercel:status` |
| Supabase 依存がある | `supabase:supabase` |
| Slack 環境変数がある | `slack:standup`・`slack:find-discussions` |

### 3-B: マシン上の導入状況を確認

各 CLI ツールを `command -v` で確認する:

```bash
command -v git && git --version
command -v gh && gh --version
command -v node && node --version
command -v python3 && python3 --version
command -v ruff && ruff --version
```

Node.js パッケージは `package.json` の `devDependencies` に記載があれば「導入予定」とみなし、`node_modules/` が存在しない場合のみインストール対象とする。

PHP の `pint` / `pest` は `vendor/` 配下に存在するか確認する。

Claude Code の MCP は `.mcp.json`（プロジェクト）と `~/.claude/claude.json`（グローバル）の両方を確認し、どちらにも設定がなければ対象とする。

### 3-C: 未導入ツールのインストール

未導入のツールを **まとめてリストアップしてユーザーに一括確認** してからインストールを実行する。1ツールずつ聞かない。

**Node.js パッケージ（`node_modules/` がない場合）:**
```bash
npm install   # または pnpm install / yarn install
```

**Node.js 開発ツール（`devDependencies` に未記載の場合）:**
```bash
npm install --save-dev eslint prettier vitest @vitest/coverage-v8
# TypeScript の場合は追加
npm install --save-dev typescript @types/node tsx
```

**Python ツール（未導入の場合）:**
```bash
pip install ruff pytest pytest-cov
```

**gh CLI（未導入の場合）:**
システムへの影響が大きいため自動インストールしない。インストールコマンドを提示してユーザーに実行を促す:
```
# macOS
brew install gh
# Linux (Ubuntu/Debian)
sudo apt install gh
```

### 3-D: Claude Code MCP の設定

未設定の MCP サーバーをプロジェクトルートの `.mcp.json` に追加する。既存の `.mcp.json` がある場合はマージする（上書きしない）。

以下の python3 コマンドで生成する:

```bash
python3 << 'PYEOF'
import json, os

# 検出結果に応じて追加するサーバーを構築（不要なものは除く）
new_servers = {
    "github": {
        "type": "stdio",
        "command": "docker",
        "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                 "ghcr.io/github/github-mcp-server"],
        "env": {}
    },
    # playwright が依存にある場合は追加:
    # "playwright": {
    #     "type": "stdio",
    #     "command": "npx",
    #     "args": ["@playwright/mcp@latest"],
    #     "env": {}
    # },
}

path = ".mcp.json"
existing = {}
if os.path.exists(path):
    with open(path) as f:
        existing = json.load(f)

servers = existing.get("mcpServers", {})
added = []
for name, config in new_servers.items():
    if name not in servers:
        servers[name] = config
        added.append(name)

existing["mcpServers"] = servers
with open(path, "w") as f:
    json.dump(existing, f, indent=2)

print(f"✓ .mcp.json を更新しました（追加: {added}）")
PYEOF
```

### 3-E: Claude Code Plugins の案内

未導入の Plugin を検出した場合、インストール方法をまとめて出力してユーザーに案内する（自動インストールはしない）:

```
📦 以下の Claude Code Plugin の導入を推奨します（未インストールのもの）:

- Supabase Plugin: claude mcp add supabase ...
- Vercel Plugin:   claude mcp add vercel ...

インストール後、/init-autonomous を再実行するか .mcp.json に手動で追記してください。
```

### 3-F: 推奨 Skills の案内

プロジェクトに関連する既存 Skills をまとめて案内する（スタック別に該当するものだけ表示）:

```
🛠️  このプロジェクトで使える Skills:
- /vercel:deploy      — Vercel へのデプロイ
- /vercel:env         — 環境変数の管理
- /supabase:supabase  — Supabase 操作全般
- /slack:standup      — Slack スタンドアップ生成
```

---

## ステップ 4: ファイルを一括生成

既存ファイルがある場合は **上書き前に確認する**。それ以外は人間の追加入力なしに生成を進める。

---

### 4-0. `.claude/settings.json`（プロジェクト固有の権限設定）

検出したスタックに応じて、`auto` モードで確認なしに実行できるコマンドを定義する。
**git は グローバル設定で `Bash(git *)` / `Bash(gh *)` として許可済みのため含めない。**

以下の手順で生成する（複数スタック検出時は `allow` 配列を自動マージ）:

**Step 1: `/tmp/` に生成**（検出スタックに合わせてコメントアウトを解除すること）

```bash
python3 << 'PYEOF'
import json, os

# 検出されたスタックに応じてコメントアウトを解除する
STACK_PERMISSIONS = {
    # "nodejs": [  # package.json 検出時
    #     "Bash(npm run *)", "Bash(npm ci)", "Bash(npm install *)",
    #     "Bash(npx *)", "Bash(node *)", "Bash(pnpm *)", "Bash(yarn *)",
    # ],
    # "laravel": [  # composer.json + artisan 検出時
    #     "Bash(php artisan *)", "Bash(composer *)",
    #     "Bash(./vendor/bin/pest *)", "Bash(./vendor/bin/pint *)",
    # ],
    # "python": [  # requirements.txt / pyproject.toml 検出時
    #     "Bash(python *)", "Bash(python3 *)", "Bash(pip install *)",
    #     "Bash(pytest *)", "Bash(ruff *)", "Bash(uvicorn *)", "Bash(gunicorn *)",
    # ],
    # "go": [  # go.mod 検出時
    #     "Bash(go build *)", "Bash(go test *)", "Bash(go run *)",
    #     "Bash(go mod *)", "Bash(go vet *)",
    # ],
    # "rust": [  # Cargo.toml 検出時
    #     "Bash(cargo build *)", "Bash(cargo test *)", "Bash(cargo run *)",
    #     "Bash(cargo clippy *)", "Bash(cargo fmt *)",
    # ],
}

existing = {}
if os.path.exists(".claude/settings.json"):
    with open(".claude/settings.json") as f:
        existing = json.load(f)

current_allow = existing.get("permissions", {}).get("allow", [])
new_allow = [p for perms in STACK_PERMISSIONS.values() for p in perms]
merged = list(dict.fromkeys(current_allow + new_allow))

if "permissions" not in existing:
    existing["permissions"] = {}
existing["permissions"]["allow"] = merged
existing["defaultMode"] = "auto"

with open("/tmp/claude_settings.json", "w") as f:
    json.dump(existing, f, indent=2)

print(f"✓ /tmp/claude_settings.json を生成しました（allow: {len(merged)} 件）")
PYEOF
```

**Step 2: プロジェクトに配置**

```bash
mkdir -p .claude && cp /tmp/claude_settings.json .claude/settings.json && echo "✓ .claude/settings.json を配置しました"
```

cp がブロックされた場合はユーザーに以下を実行してもらう:

```
! mkdir -p .claude && cp /tmp/claude_settings.json .claude/settings.json
```

---

### 4-1. `CLAUDE.md`（プロジェクトルート）

以下の内容で生成する。`{{ }}` 内はステップ 1・2 の収集情報で置き換える:

```markdown
# {{ PROJECT_NAME }} — CLAUDE.md

## ドキュメント

{{ EXISTING_DOCS が空の場合 }}
| ファイル | 内容 |
|---------|------|
| `docs/01_product-specifications.md` | 目的・ユーザー・画面一覧・画面遷移 |
| `docs/02_detailed-design.md` | 各機能の詳細仕様・バリデーション・権限 |
| `docs/03_technical-requirements.md` | 技術スタック・依存ライブラリ・制約 |
| `docs/conventions.md` | 命名規則・コーディング規約 |
| `docs/adr/` | 設計上の重要判断の記録 |
| `docs/CODEMAPS/` | ファイル責務一覧 |

**実装前に必ず `docs/01_product-specifications.md` と `docs/02_detailed-design.md` を読むこと。**

{{ EXISTING_DOCS がある場合（既存資料のパスと種別をそのまま列挙） }}
| ファイル | 内容 |
|---------|------|
| `{{ EXISTING_DOCS の各パスを行として展開 }}` | {{ 種別 }} |
| `docs/conventions.md` | 命名規則・コーディング規約 |
| `docs/adr/` | 設計上の重要判断の記録 |
| `docs/CODEMAPS/` | ファイル責務一覧 |

**実装前に必ず上記ドキュメントを読むこと。**

## 技術スタック

{{ 検出したスタックを箇条書きで記載 }}

## フォルダ構成

{{ 検出したスタックの標準的なディレクトリ構成を記載 }}

## 絶対に守るルール

- 実装前に仕様書（`docs/01_` `docs/02_`）を必ず読む
- 全エンドポイントで認証・認可を確認する
- DB操作はトランザクションでラップする
- N+1 禁止：Eager Load を明示する
- `any` 禁止：型が不明な場合は `unknown` + 型ガードを使う
- テストは新機能・バグ修正で先行作成（TDD: RED → GREEN → REFACTOR）
- 1タスク = 1画面 or 1機能。スコープを超えない
- シークレットは環境変数で管理、コードにハードコードしない
- {{ CONSTRAINTS があれば追加 }}

## ドメインエンティティ

{{ DOMAIN_ENTITIES をリスト形式で記載 }}

## ユーザーロール

{{ USER_ROLES を記載。「認証なし」の場合はその旨 }}

## スラッシュコマンド

### 全自動モード（要件 → デプロイ）
| コマンド | 役割 |
|---------|------|
| `/requirements` | 要件分析（曖昧な要望を構造化要件に変換） |
| `/design` | システム設計（DB スキーマ・API コントラクト・技術選定） |
| `/plan` | 実装計画 |
| `/tdd` | テスト駆動開発で実装 |
| `/migrate` | DB マイグレーション実行 |
| `/deploy` | デプロイ + 検証 + 自動ロールバック |
| `/rollback` | 手動ロールバック |

### サポートモード（タスク → PR）
| コマンド | 役割 |
|---------|------|
| `/analyze-task` | タスク・課題・バグ報告を実装可能な単位に分解 |
| `/plan` | 実装計画 |
| `/tdd` | テスト駆動開発で実装 |
| `/respond-review` | PR レビューコメントへの対応 |

### 共通
| コマンド | 役割 |
|---------|------|
| `/code-review` | コードレビュー（自分のコード） |
| `/commit` | Conventional Commits 形式でコミット |
| `/create-pr` | PR 作成（base は develop 固定） |
| `/build-fix` | ビルド・型エラーの修正 |
| `/test-coverage` | カバレッジ補完 |
| `/refactor-clean` | デッドコード削除 |
| `/e2e` | E2E テスト生成・実行 |
| `/update-docs` | ドキュメント同期 |
| `/update-codemaps` | コードマップ更新 |

### プロジェクト固有（このプロジェクトのみ）
| コマンド | 役割 |
|---------|------|
| `/precommit-check` | フォーマット・テスト・型チェック・静的解析を順番に実行 |
| `/audit-custom` | プロジェクト固有の静的解析を実行 |
```

---

### 4-2. `.claude/rules/`

**共通（全スタック必須）:**

#### `.claude/rules/architecture.md`

採用したアーキテクチャパターンと責務分離のルールを記載する。検出したスタックに応じて内容を変える:

- Laravel が含まれる場合: Controller（HTTP処理のみ）→ Service（ビジネスロジック）→ Repository（DB操作）の3層構成を記載
- Next.js が含まれる場合: Server Components（データフェッチ）/ Client Components（インタラクション）/ Server Actions（フォーム送信）の分離を記載
- FastAPI / Django が含まれる場合: Router/View → Service → Repository の分離を記載
- 共通: 依存の方向（上位レイヤーが下位に依存、逆は禁止）を明記

#### `.claude/rules/testing.md`

テスト戦略を記載する:
- カバレッジ目標: 80% 以上
- TDD の手順（RED → GREEN → REFACTOR）
- テスト種別: 単体テスト・統合テスト・E2Eテスト
- `{{ TEST_FRAMEWORK }}` のコマンド例（カバレッジ付きで実行する方法）
- モックの使用方針（DBは原則モックしない、外部APIはモックする）

#### `.claude/rules/git-workflow.md`

ブランチ戦略とコミット形式を記載する:
- ブランチ命名: `feature/目的_YYYYMMDD`、`fix/目的_YYYYMMDD`
- コミットメッセージ: Conventional Commits 形式（`feat:` `fix:` `refactor:` `docs:` `test:` `chore:`）
- PR の作り方: `/create-pr` コマンドを使う
- ブランチ保護: `main` / `develop` への直接プッシュ禁止

**スタック別（検出したものだけ生成）:**

#### `.claude/rules/laravel.md`（Laravel 検出時）

```markdown
# Laravel ルール

## 責務分離

Controller はHTTPリクエスト/レスポンスのみ担当する。

**Good:**
\`\`\`php
class OrderController extends Controller
{
    public function store(StoreOrderRequest $request, OrderService $service): JsonResponse
    {
        $order = $service->create($request->validated());
        return response()->json(new OrderResource($order), 201);
    }
}
\`\`\`

**Bad:**
\`\`\`php
class OrderController extends Controller
{
    public function store(Request $request): JsonResponse
    {
        // Controller にビジネスロジックを書かない
        $order = Order::create([...]);
        Mail::to($order->user)->send(new OrderConfirmation($order));
        return response()->json($order);
    }
}
\`\`\`

## Eloquent

- N+1 禁止: `with()` で Eager Load を明示する
- DB操作はトランザクションでラップする: `DB::transaction(fn() => ...)`
- `all()` 禁止: 必ず `where` か `paginate` を使う
```

#### `.claude/rules/nextjs.md`（Next.js 検出時）

```markdown
# Next.js ルール

## Server / Client Components の使い分け

データフェッチは Server Components で行う。

**Good:**
\`\`\`tsx
// app/orders/page.tsx — Server Component
export default async function OrdersPage() {
  const orders = await fetchOrders() // サーバーで実行
  return <OrderList orders={orders} />
}
\`\`\`

**Bad:**
\`\`\`tsx
'use client'
export default function OrdersPage() {
  const [orders, setOrders] = useState([])
  useEffect(() => { fetchOrders().then(setOrders) }, []) // クライアントフェッチは避ける
}
\`\`\`

## Server Actions

フォーム送信には Server Actions を使う。`api/` ルートは外部クライアント向けのみ。

## ルーティング

App Router を使用する。`pages/` ディレクトリへの新規追加は禁止。
```

#### `.claude/rules/django.md`（Django 検出時）

```markdown
# Django ルール

## 責務分離

View はHTTP処理のみ。ビジネスロジックは `services.py` に集約する。

**Good:**
\`\`\`python
# services.py
def create_order(user: User, data: dict) -> Order:
    with transaction.atomic():
        order = Order.objects.create(user=user, **data)
        send_confirmation_email(order)
        return order
\`\`\`

## ORM

- N+1 禁止: `select_related()` / `prefetch_related()` を明示する
- `all()` をそのまま使用禁止: フィルタまたはページネーションを必ず適用する
- DB操作は `transaction.atomic()` でラップする
```

#### `.claude/rules/typescript.md`（TypeScript 検出時）

```markdown
# TypeScript ルール

## 型定義

- `any` 禁止。型が不明な場合は `unknown` + 型ガードを使う
- 型定義の場所: `types/` ディレクトリ または各ドメインの `*.types.ts`

**Good:**
\`\`\`typescript
function parseResponse(data: unknown): ApiResponse {
  if (!isApiResponse(data)) throw new Error('Invalid response shape')
  return data
}
\`\`\`

**Bad:**
\`\`\`typescript
function parseResponse(data: any): any {
  return data
}
\`\`\`

## 非同期処理

`async/await` を使う。`.then().catch()` チェーンは避ける。
エラーは `try/catch` でハンドリングし、ユーザーフレンドリーなメッセージを投げる。
```

#### `.claude/rules/react.md`（React/Next.js 検出時）

```markdown
# React ルール

## コンポーネント設計

- 1コンポーネント = 1責務。200行を超えたら分割を検討する
- カスタムフックにロジックを分離する（`use` プレフィックス）

**Good:**
\`\`\`tsx
function useOrderForm(orderId: string) {
  const [state, dispatch] = useReducer(orderReducer, initialState)
  const submit = async (data: OrderFormData) => { ... }
  return { state, submit }
}

export function OrderForm({ orderId }: Props) {
  const { state, submit } = useOrderForm(orderId)
  return <form onSubmit={submit}>...</form>
}
\`\`\`

## 状態管理

- ローカル状態: `useState` / `useReducer`
- サーバー状態: TanStack Query または SWR
- グローバル状態: Context API（小規模）または Zustand（大規模）
- フォーム: React Hook Form + Zod バリデーション
```

#### `.claude/rules/vue.md`（Vue/Nuxt 検出時）

```markdown
# Vue ルール

## コンポーネント設計

- Composition API (`<script setup>`) を使う
- ロジックは `composables/use*.ts` に分離する
- Props は `defineProps` で型定義必須

## 状態管理

- Pinia を使う。Vuex は禁止
- ストアはドメイン単位で分割する（`useOrderStore`, `useUserStore` 等）
```

---

### 4-3. `.claude/commands/`

#### `.claude/commands/implement-feature.md`

```markdown
---
name: フィーチャー実装（TDD一気通貫）
description: 仕様確認 → TDD → 実装 → コードレビュー → コミットを一気通貫で実行します
---

# /implement-feature

引数として実装する機能名または Issue 番号を受け取る。

## 手順

### 1. 仕様確認

`docs/01_product-specifications.md` と `docs/02_detailed-design.md` を読む。
実装対象の機能に関するセクションを特定し、以下を整理する:
- 機能の目的と期待する動作
- 入力値・バリデーションルール
- 権限（どのロールが実行できるか）
- 境界条件・エラーケース

仕様が不明確な箇所があれば実装前にユーザーに確認する。

### 2. テストを先に書く（RED）

`{{ TEST_FRAMEWORK }}` でテストファイルを作成する。
以下のケースを網羅する:
- 正常系（ハッピーパス）
- バリデーションエラー
- 権限エラー
- 境界値

テストを実行して **FAIL することを確認する**。

### 3. 実装（GREEN）

テストがパスする最小限の実装を書く。
`.claude/rules/architecture.md` の責務分離ルールに従う。

テストを実行して **全件 PASS することを確認する**。

### 4. リファクタリング（REFACTOR）

コードの重複・命名・責務の分散を確認して改善する。
テストが引き続き PASS することを確認する。

### 5. コードレビュー

**code-reviewer** エージェントを起動してレビューを受ける。
CRITICAL・HIGH の指摘は修正してから次へ進む。

### 6. コミット

`/precommit-check` を実行してすべてパスすることを確認する。
Conventional Commits 形式でコミットする。
```

#### `.claude/commands/issue-to-pr.md`

```markdown
---
name: Issue → PR 全自動
description: GitHub Issue を読み込み、実装して PR を作成します
---

# /issue-to-pr

引数として Issue 番号を受け取る（例: `/issue-to-pr 42`）。

## 手順

### 1. Issue を読み込む

`gh issue view {{ Issue番号 }}` で Issue の内容を取得する。
以下を確認する:
- タイトルと説明
- 受け入れ条件（Acceptance Criteria）
- ラベル（`bug` / `feature` / `refactor` 等）

### 2. 仕様を確認する

`docs/01_product-specifications.md` と `docs/02_detailed-design.md` を読み、
Issue に関連するセクションを特定する。

### 3. ブランチを作成する

\`\`\`bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-{{ Issue番号 }}_YYYYMMDD
\`\`\`

### 4. 実装する

`/implement-feature` の手順（TDD一気通貫）に従って実装する。

### 5. PR を作成する

`/create-pr` を実行して PR を作成する。
PR の説明に `Closes #{{ Issue番号 }}` を含める。
```

#### `.claude/commands/spec.md`

```markdown
---
name: 仕様確認
description: 実装前に仕様書の該当箇所を読んで整理します
---

# /spec

引数として機能名・エンドポイント・画面名等を受け取る。

## 手順

### 1. 仕様書を読む

以下を順に読んで対象機能の仕様を収集する:
1. `docs/01_product-specifications.md` — 対象機能の概要・画面・遷移
2. `docs/02_detailed-design.md` — バリデーション・権限・保存ロジック

### 2. 整理して出力する

以下の形式で整理して出力する:

\`\`\`
## {{ 機能名 }} の仕様

**目的:** ...
**対象ロール:** ...
**入力項目:**
- フィールド名: バリデーションルール
**出力/結果:** ...
**エラーケース:**
- ケース: 期待する動作
**不明点:** （ある場合のみ）
\`\`\`
```

#### `.claude/commands/precommit-check.md`

```markdown
---
name: プリコミットチェック
description: フォーマット・テスト・型チェック・静的解析を順番に実行します
---

# /precommit-check

## 手順

以下を順番に実行する。いずれかが失敗したら **その場で停止して修正する**。次のステップには進まない。

### 1. フォーマット

スタックに応じて実行する:
- Laravel: `./vendor/bin/pint`
- Node.js: `npm run format` または `npx prettier --write .`
- Python: `ruff format .`

### 2. Lint

スタックに応じて実行する:
- Laravel: `./vendor/bin/pint --test`
- Node.js: `npm run lint`
- Python: `ruff check .`

### 3. 型チェック（TypeScript 使用時）

\`\`\`bash
npx tsc --noEmit
\`\`\`

### 4. テスト（カバレッジ付き）

スタックに応じて実行する:
- Laravel: `./vendor/bin/pest --coverage --min=80`
- Node.js (Vitest): `npx vitest run --coverage`
- Node.js (Jest): `npx jest --coverage`
- Python: `pytest --cov --cov-fail-under=80`

カバレッジが 80% を下回る場合は追加テストを書いてから進む。

### 5. カスタム静的解析

\`\`\`bash
bash .github/scripts/audit-custom.sh
\`\`\`

### 6. 完了報告

全ステップが PASS したら「プリコミットチェック: 全 PASS ✅」と報告する。
```

#### `.claude/commands/create-pr.md`

```markdown
---
name: PR作成
description: コミット履歴を分析してPRテンプレを埋めて作成します
---

# /create-pr

## 手順

### 1. 変更内容を収集する

\`\`\`bash
git log develop..HEAD --oneline
git diff develop...HEAD --stat
\`\`\`

全コミット（最新だけでなく全件）を分析して変更の全容を把握する。

### 2. PR の情報を整理する

- タイトル: 70文字以内、`feat:` / `fix:` / `refactor:` プレフィックスを付ける
- 変更種別: 機能追加 / バグ修正 / リファクタリング / ドキュメント / CI
- 関連 Issue: `Closes #番号` があれば記載

### 3. PR を作成する

`.github/PULL_REQUEST_TEMPLATE.md` のテンプレートを使って PR を作成する:

\`\`\`bash
git push -u origin HEAD
gh pr create --title "..." --body "$(cat <<'EOF'
## 概要
Closes #

## 変更内容
...

## チェックリスト
- [ ] テスト PASS（カバレッジ 80% 以上）
- [ ] 型チェック PASS
- [ ] フォーマット PASS
- [ ] カスタム静的解析 PASS（CRITICAL 0件）
- [ ] セキュリティ観点で確認済み（認証・認可・入力検証）

## テスト結果
EOF
)"
\`\`\`
```

#### `.claude/commands/audit-custom.md`

```markdown
---
name: カスタム静的解析
description: プロジェクト固有の静的解析を実行します
---

# /audit-custom

## 手順

### 1. スクリプトを実行する

\`\`\`bash
bash .github/scripts/audit-custom.sh
\`\`\`

### 2. 結果を確認する

- 終了コード 0: PASS
- 終了コード 1: CRITICAL 違反あり → 修正してから再実行

### 3. カスタマイズ方法

`.github/scripts/audit-custom.sh` に `docs/adr/` の決定事項に基づくチェックを追加する。

例（Laravel での認可チェック漏れ検出）:
\`\`\`bash
if grep -rn "public function" app/Http/Controllers/ | grep -v "Gate::\|can(\|authorize("; then
  echo "CRITICAL: 認可チェックなしのパブリックメソッドが存在します"
  ERRORS=$((ERRORS + 1))
fi
\`\`\`
```

---

### 4-4. `.claude/agents/`

#### `.claude/agents/code-reviewer.md`

```markdown
---
name: code-reviewer
description: コード品質・セキュリティ・パフォーマンスの観点でコードをレビューします
model: claude-sonnet-4-6
---

# コードレビューエージェント

## 役割

実装されたコードを品質・セキュリティ・パフォーマンスの3観点でレビューし、問題点を severity 別に報告する。

## トリガー条件

- `/implement-feature` 実行時（ステップ 5）
- ユーザーが「レビューして」と依頼したとき
- PR 作成前

## レビュー観点

**品質:**
- 関数・ファイルのサイズ（50行・800行を超えていないか）
- ネスト深さ（4レベル以内か）
- 命名の明確さ
- `any` / ミューテーションの使用
- `console.log` の残存

**セキュリティ:**
- 認証・認可チェックの漏れ
- 入力値バリデーションの欠如
- シークレットのハードコード
- SQL インジェクション・XSS の可能性

**パフォーマンス:**
- N+1 クエリ
- 不要な全件取得
- メモ化すべき重い計算

## 出力形式

\`\`\`
## コードレビュー結果

### CRITICAL（必ず修正）
- [ ] ファイル名:行番号 — 問題の説明

### HIGH（強く推奨）
- [ ] ファイル名:行番号 — 問題の説明

### MEDIUM（改善推奨）
- [ ] ファイル名:行番号 — 問題の説明

### 総評
（全体の品質評価を2〜3文で）
\`\`\`

CRITICAL が 0 件になるまでレビューサイクルを繰り返す。
```

#### `.claude/agents/tdd-writer.md`

```markdown
---
name: tdd-writer
description: テストを先に書いてRED→GREEN→REFACTORサイクルを回します
model: claude-sonnet-4-6
---

# TDDライターエージェント

## 役割

新機能・バグ修正に対してテストファーストで開発を進める。RED → GREEN → REFACTOR サイクルを厳守する。

## トリガー条件

- 新機能の実装依頼
- バグ修正の依頼
- `/implement-feature` の「テストを先に書く」フェーズ

## 手順

1. 仕様を確認して以下のテストケースを列挙する:
   - 正常系（ハッピーパス）
   - バリデーションエラー（各フィールド）
   - 権限エラー
   - 境界値・エッジケース

2. `{{ TEST_FRAMEWORK }}` でテストファイルを作成する

3. テストを実行して **FAIL することを確認する（RED）**

4. 最小限の実装を書く

5. テストを実行して **PASS することを確認する（GREEN）**

6. コードを改善する（REFACTOR）。テストが引き続き PASS することを確認する

7. カバレッジを確認する。80% 未満なら追加テストを書く

## 出力形式

- `🔴 RED: テスト X 件作成、全件 FAIL 確認`
- `🟢 GREEN: 全 X 件 PASS`
- `♻️  REFACTOR: 改善内容を箇条書き`
- `📊 カバレッジ: XX%`
```

#### `.claude/agents/security-reviewer.md`

```markdown
---
name: security-reviewer
description: 認証・認可・入力検証・シークレット漏洩をチェックします
model: claude-sonnet-4-6
---

# セキュリティレビューエージェント

## 役割

コードのセキュリティ脆弱性を検出し、修正方法を提示する。

## トリガー条件

- 認証・認可に関わるコードを書いたとき
- 入力値を受け取るエンドポイントを作ったとき
- コミット前の最終チェック
- シークレットを扱うコードを変更したとき

## チェック項目

- [ ] 全エンドポイントに認証チェックがあるか
- [ ] ロールベースの認可チェックがあるか
- [ ] 全ユーザー入力がバリデーションされているか
- [ ] シークレットが環境変数から読まれているか（ハードコードなし）
- [ ] SQL クエリがパラメータ化されているか
- [ ] HTML 出力がエスケープされているか
- [ ] エラーメッセージに内部情報が含まれていないか
- [ ] セッション・JWT の適切な管理

## 出力形式

\`\`\`
## セキュリティレビュー結果

### CRITICAL（即座に修正必須）
- [ ] 問題の説明と修正方法

### HIGH（コミット前に修正）
- [ ] 問題の説明と修正方法

### 問題なし
セキュリティ上の問題は検出されませんでした ✅
\`\`\`

CRITICAL が存在する場合は修正するまで STOP する。
```

#### `.claude/agents/build-fixer.md`

```markdown
---
name: build-fixer
description: ビルドエラー・型エラーを最小差分で修正します
model: claude-sonnet-4-6
---

# ビルドフィクサーエージェント

## 役割

ビルドエラー・型エラーを分析し、最小限の変更で修正する。アーキテクチャの変更は行わない。

## トリガー条件

- ビルドが失敗したとき
- TypeScript の型エラーが発生したとき
- CI が RED になったとき

## 手順

1. エラーメッセージを読んで根本原因を特定する
2. 関連ファイルを読む（エラー箇所と周辺コンテキスト）
3. 最小差分の修正を適用する
4. 再ビルドして修正を確認する
5. 修正内容を簡潔に報告する

## 制約

- 修正範囲をエラーの直接原因に限定する
- 「ついでに」リファクタリングしない
- アーキテクチャ上の判断が必要な場合はユーザーに確認する

## 出力形式

\`\`\`
## ビルドエラー修正

**根本原因:** ...
**修正ファイル:** ファイル名:行番号
**修正内容:** 変更の説明
**結果:** ✅ ビルド成功 / ❌ 別のエラーが発生（詳細）
\`\`\`
```

---

### 4-5. `docs/` ディレクトリ構造

**`EXISTING_DOCS` がある場合の処理:**

既存資料のパスが指定されている場合、そのファイルを読み込んで内容を把握した上で以下を行う：

- 仕様書に相当する資料 → `docs/01_product-specifications.md` に内容を転記（または `CLAUDE.md` の参照パスを既存ファイルに書き換え）
- 設計書に相当する資料 → `docs/02_detailed-design.md` に内容を転記（または同様に参照パスを書き換え）
- `docs/03_technical-requirements.md`・`docs/conventions.md` は既存資料から読み取れる情報を元に生成する

いずれの方法を取るかはファイル構成の状況に応じて判断し、ユーザーに確認してから進める。

**`EXISTING_DOCS` がない場合の処理:**

以下のテンプレートを生成する。

#### `docs/01_product-specifications.md`

```markdown
# プロダクト仕様書

## 目的

<!-- このプロダクトが解決する問題を1〜3文で記入 -->

## ターゲットユーザー

<!-- 誰が使うか -->

## 画面一覧

| 画面名 | URL | 説明 |
|-------|-----|------|
| <!-- ここに記入 --> | | |

## 画面遷移

<!-- 主要なユーザーフローを箇条書きまたは図で記入 -->

## 主要ユーザーストーリー

<!-- As a [ロール], I want to [操作], so that [目的] の形式で記入 -->
```

#### `docs/02_detailed-design.md`

```markdown
# 詳細設計書

<!-- 各機能の詳細仕様を記入。AI エージェントはこのファイルを実装前に必ず読む -->

## 機能別仕様

### 機能名

**目的:** <!-- ここに記入 -->

**対象ロール:** <!-- ここに記入 -->

**入力:**

| フィールド | 型 | 必須 | バリデーション |
|----------|---|------|-------------|
| <!-- ここに記入 --> | | | |

**処理ロジック:** <!-- ここに記入 -->

**出力/レスポンス:** <!-- ここに記入 -->

**エラーケース:**

| 条件 | エラーメッセージ | HTTPステータス |
|-----|--------------|-------------|
| <!-- ここに記入 --> | | |
```

#### `docs/03_technical-requirements.md`

```markdown
# 技術要件

## 技術スタック

{{ 検出したスタックを詳細に記載 }}

## 依存ライブラリ

<!-- 主要ライブラリとバージョン・用途を記載 -->

## 制約

{{ CONSTRAINTS があれば記載。なければ「特になし」 }}

## 環境変数

| 変数名 | 説明 | 必須 |
|-------|-----|------|
| <!-- ここに記入 --> | | |

## 外部依存サービス

<!-- API、外部サービス等 -->
```

#### `docs/conventions.md`

スタックに応じた命名規則・コーディング規約を生成する:

- **変数・関数名**: camelCase（JS/TS）、snake_case（Python/PHP）、camelCase（Go）
- **ファイル名**: kebab-case（JS/TS）、snake_case（Python/PHP）
- **クラス名**: PascalCase（全言語共通）
- **定数**: UPPER_SNAKE_CASE
- **DB テーブル名**: snake_case、複数形
- **API エンドポイント**: kebab-case、RESTful 設計

#### `docs/adr/000-template.md`

```markdown
# ADR-000: 決定事項のタイトル

**ステータス:** proposed / accepted / deprecated / superseded

**日付:** YYYY-MM-DD

## コンテキスト

<!-- なぜこの決定が必要だったか。背景・制約・問題 -->

## 検討した選択肢

1. **選択肢A** — メリット / デメリット
2. **選択肢B** — メリット / デメリット

## 決定

<!-- 選択した選択肢と理由 -->

## 結果

<!-- この決定による影響（良い面・悪い面） -->

<!-- コードで検証可能な制約があれば .github/scripts/audit-custom.sh に追加する -->
```

#### `docs/CODEMAPS/backend.md`

```markdown
# バックエンド コードマップ

| ファイルパス | 責務 | 主なクラス/関数 |
|-----------|-----|-------------|
| <!-- ここに記入 --> | | |
```

#### `docs/CODEMAPS/frontend.md`

```markdown
# フロントエンド コードマップ

| ファイルパス | 責務 | 主なコンポーネント |
|-----------|-----|--------------|
| <!-- ここに記入 --> | | |
```

#### `docs/playbooks/new-feature.md`

```markdown
# 新機能追加 標準手順書

## 手順

1. **Issue 確認** — `gh issue view {{ 番号 }}` で要件を確認する
2. **仕様確認** — `/spec {{ 機能名 }}` で仕様書の該当箇所を整理する
3. **ADR 確認** — `docs/adr/` を読んで関連する設計決定を把握する
4. **ブランチ作成** — `feature/機能名_YYYYMMDD`
5. **TDD 実装** — `/implement-feature {{ 機能名 }}`（テストファースト）
6. **プリコミットチェック** — `/precommit-check`（全 PASS を確認）
7. **PR 作成** — `/create-pr`
8. **コードマップ更新** — `docs/CODEMAPS/` を更新する
```

---

### 4-6. `.github/`

#### `.github/workflows/ci.yml`

検出したスタックに応じて以下のジョブを並列実行する CI を生成する:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
```

**Laravel 検出時のジョブ:**

```yaml
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
      - run: composer install --no-interaction
      - run: ./vendor/bin/pint --test

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          coverage: xdebug
      - run: composer install --no-interaction
      - run: ./vendor/bin/pest --coverage --coverage-clover=coverage.xml --min=80
      - name: Post coverage comment
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7

  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: composer audit
```

**Node.js 検出時のジョブ:**

```yaml
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test -- --coverage
      - name: Post coverage comment
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build

  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --audit-level=high
```

**Python 検出時のジョブ:**

```yaml
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install ruff
      - run: ruff check . && ruff format --check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: pytest --cov --cov-fail-under=80 --cov-report=xml

  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit
      - run: pip-audit
```

**共通追加ジョブ（全スタック）:**

```yaml
  custom-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash .github/scripts/audit-custom.sh
```

#### `.github/scripts/audit-custom.sh`

```bash
#!/usr/bin/env bash
# プロジェクト固有の静的解析
# 終了コード: 0=OK, 1=CRITICAL 違反あり
set -euo pipefail

ERRORS=0

# ─────────────────────────────────────────────────────────────────
# CHECK 1: （プロジェクト固有ルールをここに追加）
# docs/adr/ の決定事項をコードで検証するチェックを書く
# ─────────────────────────────────────────────────────────────────

echo "カスタム静的解析: チェック未設定"
echo "docs/adr/ を参考にプロジェクト固有のバグパターンを追加してください"

if [ "$ERRORS" -gt 0 ]; then
  echo "❌ CRITICAL 違反: ${ERRORS} 件"
  exit 1
fi

echo "✅ カスタム静的解析: PASS"
exit 0
```

#### `.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## 概要

<!-- 何を・なぜ変更したか -->

Closes #

## 変更内容

- [ ] 機能追加
- [ ] バグ修正
- [ ] リファクタリング
- [ ] ドキュメント
- [ ] CI / 設定変更

## チェックリスト

- [ ] テスト PASS（カバレッジ 80% 以上）
- [ ] 型チェック PASS
- [ ] フォーマット PASS
- [ ] カスタム静的解析 PASS（CRITICAL 0件）
- [ ] セキュリティ観点で確認済み（認証・認可・入力検証）

## テスト結果

<!-- カバレッジ出力を貼る -->
```

#### `.github/ISSUE_TEMPLATE/feature.yml`

```yaml
name: 機能追加
description: 新機能の追加リクエスト
title: "feat: "
labels: ["feature"]
body:
  - type: textarea
    id: description
    attributes:
      label: 機能の説明
    validations:
      required: true
  - type: textarea
    id: acceptance-criteria
    attributes:
      label: 受け入れ条件
    validations:
      required: true
  - type: textarea
    id: additional-context
    attributes:
      label: 補足情報
```

#### `.github/ISSUE_TEMPLATE/bug.yml`

```yaml
name: バグ報告
description: バグの報告
title: "fix: "
labels: ["bug"]
body:
  - type: textarea
    id: description
    attributes:
      label: 問題の説明
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: 再現手順
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: 期待する動作
    validations:
      required: true
  - type: textarea
    id: environment
    attributes:
      label: 環境
```

#### `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
    ignore:
      - dependency-name: "*"
        update-types: ["version-update:semver-major"]
```

検出したスタックに応じて `npm` / `pip` / `composer` / `gomod` を追加する。

#### `.github/labeler.yml`

```yaml
backend:
  - changed-files:
    - any-glob-to-any-file:
      - 'app/**'
      - 'src/**/*.php'
      - 'src/**/*.py'
      - 'src/**/*.go'

frontend:
  - changed-files:
    - any-glob-to-any-file:
      - 'src/components/**'
      - 'src/pages/**'
      - 'src/app/**'
      - '**/*.tsx'
      - '**/*.vue'

migration:
  - changed-files:
    - any-glob-to-any-file:
      - 'database/migrations/**'
      - 'migrations/**'
      - 'alembic/**'

tests:
  - changed-files:
    - any-glob-to-any-file:
      - '**/*.test.ts'
      - '**/*.spec.ts'
      - '**/*_test.go'
      - 'tests/**'

ci:
  - changed-files:
    - any-glob-to-any-file:
      - '.github/**'
```

---

### 4-7. 開発ツール設定ファイル

スタックに応じて以下を生成する。既存ファイルがある場合は上書き前に確認する。

#### `eslint.config.js`（Node.js/TypeScript 検出時）

```js
import js from '@eslint/js'

export default [
  js.configs.recommended,
  {
    rules: {
      'no-unused-vars': 'error',
      'no-console': 'warn',
    },
  },
]
```

#### `prettier.config.js`（Node.js 検出時）

```js
export default {
  semi: false,
  singleQuote: true,
  trailingComma: 'all',
  printWidth: 100,
}
```

#### `tsconfig.json`（TypeScript 検出時・存在しない場合のみ生成）

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitAny": true,
    "skipLibCheck": true,
    "esModuleInterop": true
  }
}
```

#### `pyproject.toml` への ruff 設定追加（Python 検出時）

既存の `pyproject.toml` がある場合はマージ、ない場合は新規作成する:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = []
```

---

### 4-8. Git フック

#### Husky（Node.js 検出時）

`devDependencies` に `husky` がなければ追加してセットアップする。ユーザーに確認してから実行する:

```bash
npm install --save-dev husky lint-staged
npx husky init
```

`.husky/pre-commit` を生成する:

```bash
#!/bin/sh
npx lint-staged
```

`package.json` に `lint-staged` 設定を追加する:

```json
{
  "lint-staged": {
    "*.{ts,tsx,js,jsx}": ["prettier --write", "eslint --fix"],
    "*.{md,json,yml}": ["prettier --write"]
  }
}
```

#### pre-commit（Python 検出時）

`pre-commit` が未導入の場合はインストールを促す。`.pre-commit-config.yaml` を生成する:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

### 4-9. エディタ設定

#### `.editorconfig`（全スタック）

```
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.php]
indent_size = 4

[*.py]
indent_size = 4

[Makefile]
indent_style = tab
```

#### `.vscode/extensions.json`（スタックに合わせて該当するものだけ含める）

```json
{
  "recommendations": [
    "EditorConfig.EditorConfig",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-typescript-next",
    "charliermarsh.ruff",
    "ms-python.python",
    "bmewburn.vscode-intelephense-client",
    "onecentlin.laravel-blade"
  ]
}
```

#### `.vscode/settings.json`（スタックに合わせて生成）

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "[php]": {
    "editor.defaultFormatter": "bmewburn.vscode-intelephense-client"
  }
}
```

---

### 4-10. プロジェクト側 hook（スタック別デバッグ出力検知）

検出スタックに応じて `.claude/hooks/debug-output-detector.py` を生成し、編集直後に言語固有のデバッグ出力（`console.log` / `print()` / `var_dump()` 等）を検知する。グローバル側ではスタック非依存の検知ができないため、プロジェクト側で対応する設計。

#### `.claude/settings.json` への配線追加

**Step 1: `/tmp/` でマージ**

```bash
python3 << 'PYEOF'
import json, os

existing = {}
if os.path.exists(".claude/settings.json"):
    with open(".claude/settings.json") as f:
        existing = json.load(f)

new_hook = {
    "matcher": "Edit|Write|MultiEdit",
    "hooks": [{"type": "command", "command": "python3 .claude/hooks/debug-output-detector.py"}]
}

hooks = existing.setdefault("hooks", {})
post_tool = hooks.setdefault("PostToolUse", [])
if new_hook["matcher"] not in [h.get("matcher") for h in post_tool]:
    post_tool.append(new_hook)

with open("/tmp/claude_settings.json", "w") as f:
    json.dump(existing, f, indent=2)

print("✓ /tmp/claude_settings.json に hooks を追加しました")
PYEOF
```

**Step 2: プロジェクトに配置**

```bash
mkdir -p .claude && cp /tmp/claude_settings.json .claude/settings.json && echo "✓ 配置しました"
```

cp がブロックされた場合:

```
! mkdir -p .claude && cp /tmp/claude_settings.json .claude/settings.json
```

#### `.claude/hooks/debug-output-detector.py`

**Step 1: `/tmp/` に生成**（不要な言語の行は削除すること）

```bash
cat > /tmp/debug-output-detector.py << 'HEREDOC'
#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): 言語別デバッグ出力を即時警告"""
import json, sys, re

try:
    data = json.load(sys.stdin)
    path = data.get('tool_input', {}).get('file_path', '')
    if not path:
        sys.exit(0)

    PATTERNS = {
        ('.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs'): [r'console\.log', r'console\.debug', r'\bdebugger\b'],
        ('.py',):  [r'\bprint\(', r'\bbreakpoint\(', r'pdb\.set_trace'],
        ('.php',): [r'\bvar_dump\(', r'\bprint_r\(', r'\bdd\(', r'\bdie\('],
        ('.rb',):  [r'\bbinding\.pry\b', r'\bbyebug\b'],
        ('.go',):  [r'fmt\.Println\('],
        ('.rs',):  [r'\bdbg!', r'\bprintln!'],
    }

    matched = next((ps for exts, ps in PATTERNS.items() if any(path.endswith(e) for e in exts)), None)
    if not matched:
        sys.exit(0)

    try:
        content = open(path).read()
    except Exception:
        sys.exit(0)

    found = []
    for n, line in enumerate(content.splitlines(), 1):
        if any(re.search(p, line) for p in matched):
            found.append((n, line.strip()))

    if found:
        print(f'⚠️  デバッグ出力を検出: {path}')
        for n, line in found[:5]:
            print(f'  {n}: {line}')
except SystemExit:
    raise
except Exception:
    sys.exit(0)
HEREDOC
```

**Step 2: プロジェクトに配置**

```bash
mkdir -p .claude/hooks && cp /tmp/debug-output-detector.py .claude/hooks/debug-output-detector.py && echo "✓ 配置しました"
```

cp がブロックされた場合:

```
! mkdir -p .claude/hooks && cp /tmp/debug-output-detector.py .claude/hooks/debug-output-detector.py
```

**設計原則**: 100 行以下・単一責務・予期せぬエラーは `exit 0`・ネットワーク通信禁止（グローバル hook と同じ規約）。

---

### 4-11. スタック固有の品質ガード設定

検出スタックに応じて、品質ガード用の追加設定をプロジェクトに生成する。

#### Web フロントエンド検出時（Next.js / React / Vue / Nuxt）

`eslint.config.js`（または既存の設定）にアクセシビリティチェックを追加:

```js
// React 系
import jsxA11y from 'eslint-plugin-jsx-a11y'

export default [
  // ...
  {
    plugins: { 'jsx-a11y': jsxA11y },
    rules: jsxA11y.configs.recommended.rules,
  },
]
```

devDependencies に追加: `eslint-plugin-jsx-a11y`（React 系）または `eslint-plugin-vuejs-accessibility`（Vue 系）。

#### Web プロジェクト検出時（フロント or バック問わず HTTP サービス）

`package.json` に Lighthouse CI スクリプトを追加（テンプレートのみ・実 URL は後でユーザーが記入）:

```json
{
  "scripts": {
    "lighthouse": "lhci autorun"
  },
  "devDependencies": {
    "@lhci/cli": "^0.13.0"
  }
}
```

`.github/workflows/lighthouse.yml` のテンプレートも生成（プレビュー URL 取得後にユーザーが有効化）。

#### API サーバー検出時（Express / FastAPI / Laravel など）

`package.json` または `pyproject.toml` などにベンチマークツールを追加（テンプレート）:
- Node.js: `autocannon`
- Python: `pytest-benchmark`
- PHP: `phpbench`

これらは初期生成のみ。実際の測定対象・閾値はプロジェクトで決める。

---

## ステップ 5: 残タスクを出力して終了

生成完了後、以下の形式で出力する:

```
✅ 自動生成完了（{{ 生成したファイル数 }} ファイル）

📝 次にあなたがやること（この順番で）:

【最優先：仕様書】
1. docs/01_product-specifications.md を書く
   → 画面一覧・画面遷移・主要ユーザーストーリー

2. docs/02_detailed-design.md を書く
   → 各機能の入力項目・バリデーションルール・権限・保存ロジック

【設計の記録】
3. docs/adr/ に設計上の重要な判断を記録する（1決定 1ファイル）
   → 「なぜこのフレームワークか」「なぜこのDB設計か」等
   → ADR-000-template.md をコピーして番号付きで作成する

【静的解析のカスタマイズ】
4. .github/scripts/audit-custom.sh にプロジェクト固有のチェックを追加する
   → ADR で決定した制約をコードで検出するルールを書く

【仕上げ】
5. CLAUDE.md の「絶対ルール」を実際の制約に合わせて調整する
6. docs/CODEMAPS/ をコード実装が進んだら随時更新する

⚠️  2, 3, 4 が薄いほどエージェントの判断品質が下がります
   仕様書が空のままエージェントに実装を依頼すると、仮定だらけのコードが生成されます

生成したファイル一覧:
{{ 生成したファイルのパスをリスト形式で出力 }}
```
