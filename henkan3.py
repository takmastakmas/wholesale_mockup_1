import streamlit as st
import pandas as pd
import mojimoji
from datetime import datetime

# -----------------------------
# 1. 大容量データに備えてキャッシュを利用
# -----------------------------
@st.cache_data
def load_excel(file):
    """
    アップロードされたExcelファイルを読み込み、DataFrameを返す関数。
    Streamlitのキャッシュ機能を利用して、再読み込みを高速化する。
    """
    # 必要に応じて、chunk単位で読み込む方法もあるが、単純化のためここでは一括読み込み。
    return pd.read_excel(file)

# -----------------------------
# 2. アプリのタイトルとファイルアップローダー
# -----------------------------
st.title("卸売データ->配分作成用データ変換アプリ")
uploaded_file = st.file_uploader("エクセルファイルをアップロードしてください", type=["xlsx", "xls"])

# -----------------------------
# 3. ファイル読み込みとデータ前処理
# -----------------------------
# セッションステートの初期化
if "filter_applied" not in st.session_state:
    st.session_state["filter_applied"] = False
if "proceed_next" not in st.session_state:
    st.session_state["proceed_next"] = False

if uploaded_file is not None:
    try:
        df = load_excel(uploaded_file)

        # 必須列のチェック
        required_columns = [
            "得意先名１", "得意先名２", "売上日付",
            "商品名", "数量", "売上金額", "得意先コード"
        ]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            st.error(f"以下の必須列が不足しています: {missing_cols}")
        else:
            # 前処理
            df["得意先名２"] = df["得意先名２"].fillna("")
            df["得意先名"] = df["得意先名１"].astype(str) + df["得意先名２"].astype(str)
            df.drop(columns=["得意先名１", "得意先名２"], inplace=True)
            df["売上日付"] = pd.to_datetime(df["売上日付"], errors="coerce")
            df["年月"] = df["売上日付"].dt.to_period("M")

            # 得意先名から特定の文字列を削除
            df["得意先名"] = df["得意先名"].str.replace("（株）", "", regex=False)
            df["得意先名"] = df["得意先名"].str.replace("（有）", "", regex=False)
            df["得意先名"] = df["得意先名"].str.replace("㈱", "", regex=False)
            df["得意先名"] = df["得意先名"].str.replace("(有)", "", regex=False)
            df["得意先名"] = df["得意先名"].str.replace("(株)", "", regex=False)
            df["得意先名"] = df["得意先名"].str.replace("(株）", "", regex=False)
            df["得意先名"] = df["得意先名"].str.replace("（株)", "", regex=False)
            
            # 得意先名の先頭のスペースを削除
            df["得意先名"] = df["得意先名"].str.lstrip()

            # 全角カタカナに変換（object型のみ）
            for column in df.select_dtypes(include=["object"]).columns:
                df[column] = df[column].apply(
                    lambda x: mojimoji.han_to_zen(x, kana=True, digit=False, ascii=False) if isinstance(x, str) else x
                )
            # 売上金額が0の行を削除
            df = df[df["売上金額"] != 0]
            # 得意先名が「現金売上」から始まる行を削除
            df = df[~df["得意先名"].str.startswith("現金売上", na=False)]
            # 売上区分が「売上」か「返品」以外の行を削除
            df = df[df["売上区分"].isin(["売上", "返品"])]
            
            # -----------------------------
            # 4. フィルタリング操作 (チェックボックス & キーワード)
            # -----------------------------
            # フィルター条件
            st.write("▼ フィルター条件を選択してください。複数選択可能です。")
            flt_switch = st.checkbox("Nintendo Switch")
            flt_switch_inverse = st.checkbox("Nintendo Switch以外")
            flt_tomica = st.checkbox("トミカ")
            flt_pmcard = st.checkbox("ポケモンカード")
            flt_gundam = st.checkbox("ガンダム")
            keyword = st.text_input("商品名に含まれるキーワードを入力（任意）:")

            # フィルターを適用するボタン
            if st.button("フィルターを適用する"):
                # フィルター処理
                filtered_df = df.copy()

                # Nintendo Switchフィルター
                if flt_switch:
                    filtered_df = filtered_df[
                        (filtered_df["商品名"].str.startswith("Nintendo Switch", na=False)) |
                        (filtered_df["商品名"].str.startswith("NS", na=False))
                    ]

                # Nintendo Switch以外
                if flt_switch_inverse:
                    filtered_df = filtered_df[
                        ~(
                            filtered_df["商品名"].str.startswith("Nintendo Switch", na=False) |
                            filtered_df["商品名"].str.startswith("NS", na=False)
                        )
                    ]

                # トミカ
                if flt_tomica:
                    filtered_df = filtered_df[filtered_df["商品名"].str.startswith("トミカ", na=False)]

                # ポケモンカード
                if flt_pmcard:
                    filtered_df = filtered_df[filtered_df["商品名"].str.startswith("PMカード", na=False)]

                # ガンダム
                if flt_gundam:
                    filtered_df = filtered_df[filtered_df["商品名"].str.contains("ガンダム", na=False, regex=True)]

                # キーワード
                if keyword:
                    filtered_df = filtered_df[filtered_df["商品名"].str.contains(keyword, na=False, regex=True)]

                # フィルター後のデータをセッションステートに保存しておく
                st.session_state["filtered_df"] = filtered_df
                st.session_state["filter_applied"] = True
                st.session_state["proceed_next"] = False  # 次のステップはまだ押されていない

            # -----------------------------
            # 5. フィルター後のデータ表示
            # -----------------------------
            # フィルターが適用されていたらフィルター後のデータを表示
            if st.session_state["filter_applied"]:
                filtered_df = st.session_state["filtered_df"]
                # 表示列を制限（売上日付、商品名、得意先名、売上金額）
                display_df = filtered_df[["売上日付", "得意先名", "商品名", "売上金額"]]
                st.write("▼ フィルター後のデータ:")
                st.dataframe(display_df)

                # 次に進むボタン
                if st.button("次に進む"):
                    st.session_state["proceed_next"] = True

            # -----------------------------
            # 6. 集計とダウンロードボタン
            # -----------------------------
            # 次に進むボタンが押されたら、その先の処理を表示
            if st.session_state["proceed_next"]:
                # 再度 filtered_df を取り出し（空チェック）
                filtered_df = st.session_state["filtered_df"]

                # ここで、得意先を複数選択して追加絞り込み
                # 折りたたみ可能なセクション
                with st.expander("▼ 得意先で絞り込み（任意）", expanded=True):
                    # 得意先名のリストをソートして提示すると使いやすい
                    customer_options = sorted(filtered_df["得意先名"].unique())

                    # 初回実行時にすべてのチェックボックスをTrueに設定
                    if "customer_checkboxes" not in st.session_state:
                        st.session_state["customer_checkboxes"] = {customer: True for customer in customer_options}

                    # 全てのチェックを外すボタン
                    if st.button("全てのチェックを外す"):
                        for customer in customer_options:
                            st.session_state["customer_checkboxes"][customer] = False

                    # 全てのチェックを入れるボタン
                    if st.button("全てにチェックを入れる"):
                        for customer in customer_options:
                            st.session_state["customer_checkboxes"][customer] = True
                            
                    # 数字から始まる得意先のチェックを外すボタン
                    if st.button("数字から始まる得意先のチェックを外す"):
                        for customer in customer_options:
                            if customer[0].isdigit():  # 得意先名の最初の文字が数字か判定
                                st.session_state["customer_checkboxes"][customer] = False

                    # チェックボックスを動的に生成
                    selected_customers = []
                    for customer in customer_options:
                        is_checked = st.checkbox(
                            customer, value=st.session_state["customer_checkboxes"][customer], key=f"checkbox_{customer}"
                        )
                        st.session_state["customer_checkboxes"][customer] = is_checked
                        if is_checked:
                            selected_customers.append(customer)

                if selected_customers:
                    filtered_df = filtered_df[filtered_df["得意先名"].isin(selected_customers)]
                else:
                    st.warning("少なくとも1つの得意先を選択してください。")

                if not filtered_df.empty:
                    result = (
                        filtered_df.groupby(["得意先コード", "得意先名", "年月"])
                        .agg(
                            売上日付ユニーク数=("売上日付", "nunique"),
                            数量合計=("数量", "sum"),
                            売上金額合計=("売上金額", "sum"),
                        )
                        .reset_index()
                    )
                    st.write("▼ 集計結果:")
                    st.dataframe(result)

                    csv = result.to_csv(index=False).encode("utf-8")
                    now_str = datetime.now().strftime("%Y%m%d_%H%M")
                    
                    # ユーザーにファイル名を入力させる
                    default_filename = f"集計結果_{now_str}.csv"
                    user_filename = st.text_input("保存するファイル名を入力してEnterを押してください（拡張子 .csv を含む）", value=default_filename)

                    # ファイル名確認ボタン
                    if st.button("ファイル名確認"):
                        if user_filename:
                            st.success(f"入力されたファイル名: {user_filename}")
                        else:
                            st.error("ファイル名を入力してください。")
                    
                    # ダウンロードボタン
                    if st.download_button(
                        label="集計結果をCSVでダウンロード",
                        data=csv,
                        file_name=user_filename,
                        mime="text/csv"
                    ):
                        st.success(f"ファイル {user_filename} を保存しました！")
                    
                else:
                    st.warning("フィルター後のデータが空でした。条件を見直してください。")

    except Exception as e:
        st.error(f"エクセルファイルの読み込み中にエラーが発生しました: {e}")
