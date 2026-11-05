# RiseSimKivy

モンハンライズ スキルシミュレータ [RiseSim](https://github.com/EXXXI/RiseSim) のコアを  
**Python + Kivy** に移植した Android APK 対応プロジェクトです。

## 機能

- スキル選択 → 装備検索 → 結果表示（Kivy GUI）
- **OR-Tools ILP 検索**（デスクトップ）
- **Pure-Python フォールバック検索**（Android / ortools なし環境）
- 護石・除外固定・傀異錬成・理想錬成・**風雷合一**

## デスクトップで起動

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

コンソールテスト:
```bash
python test_search.py
python test_furai.py
```

## GitHub で APK をビルドする

### 1. リポジトリ作成 & プッシュ

```bash
cd RiseSimKivy
git init
git add .
git commit -m "RiseSim Kivy Android project"
git branch -M main
git remote add origin https://github.com/<YOUR_USER>/RiseSimKivy.git
git push -u origin main
```

### 2. Actions でビルド

1. GitHub リポジトリ → **Actions** タブ
2. **Build Android APK** ワークフローを選択
3. **Run workflow** → debug_build = true で実行
4. 完了後 **Artifacts** から `RiseSim-apk` をダウンロード

タグを付けて push すると Release にも APK が添付されます。

```bash
git tag v0.1.0
git push origin v0.1.0
```

### 3. ローカルで Buildozer する場合

Linux (または WSL2) が必要です。

```bash
sudo apt-get install -y git unzip openjdk-17-jdk autoconf libtool \
  pkg-config zlib1g-dev libncurses5-dev cmake libffi-dev libssl-dev
pip install cython==0.29.36 buildozer==1.5.0
buildozer android debug
# → bin/risesim-0.1.0-arm64-v8a-debug.apk
```

## プロジェクト構成

```
RiseSimKivy/
├── main.py                 # Kivy アプリ入口
├── buildozer.spec          # Android ビルド設定
├── requirements.txt        # デスクトップ用
├── core/
│   ├── models.py
│   ├── data_loader.py
│   ├── searcher.py         # OR-Tools 版
│   └── searcher_pure.py    # Android 用 Pure Python 版
├── data/                   # MHR_*.csv
├── save/                   # charm / clude / ideal など
└── .github/workflows/
    └── build-android.yml   # GitHub Actions
```

## Android での注意

- Google OR-Tools のネイティブバイナリは Android 向けに同梱していないため、  
  **Pure-Python 検索エンジン**が自動で使われます（候補数を絞った列挙＋貪欲装飾品）。
- 複雑な条件ではデスクトップ版（OR-Tools）の方が高速・網羅的です。
- 初回の GitHub Actions ビルドは SDK/NDK 取得のため **30〜60分** かかることがあります。

## ライセンス

元プロジェクト RiseSim は MIT License。本移植もそれに準じます。
