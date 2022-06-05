from collections import Counter

import MeCab
import altair as alt
import pandas as pd
import streamlit as st


# df前処理
def prepare_df(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df['時間'] = pd.to_datetime(df['時間'])
    df['時間'] = df['時間'].dt.tz_convert('Asia/Tokyo')
    df['時刻'] = df['時間'].dt.hour
    return df


# いいね数ヒストグラム
def creat_hist_like(df):
    hist_like = alt.Chart(df, title=f'いいね数の傾向: n = {len(df["いいね"])}').mark_bar().encode(
        alt.X('いいね', bin=alt.Bin(extent=[0, df['いいね'].max()], step=5), title='いいね数'),
        alt.Y('count()', title='回数'),
        tooltip=['count()']
    )
    return hist_like


# 時間帯ごとの傾向
def create_trend_by_time(df):
    time_df = df[['時刻', 'いいね']]
    time_df = time_df.sort_values(by=['時刻'], ascending=True)
    grouped = time_df.groupby('時刻')

    mean = grouped.mean()
    mean.columns = ['平均いいね数']
    size = grouped.size()
    base_time = pd.DataFrame([0] * 24, index=list(range(0, 24)))
    base_time.index.name = '時刻'

    result = pd.concat([base_time, mean, size], axis=1).fillna(0)
    result.columns = ['0', '平均いいね数', 'ツイート数']
    result = result[['平均いいね数', 'ツイート数']]
    result = result.reset_index()

    base = alt.Chart(result, title=f'時間帯ごとの傾向: n={len(time_df["いいね"])}').encode(x='時刻:O')
    bar_like_average = base.mark_bar().encode(y='平均いいね数:Q', tooltip=['平均いいね数'])
    line_num_tweet = base.mark_line(color='blue').encode(y='ツイート数:Q', tooltip=['ツイート数'])
    return bar_like_average, line_num_tweet


# 等級と文字数ヒストグラム
def create_hist_strnum_by_grade(df):
    df.loc[df['いいね'] >= 100, '等級'] = 'A'
    df.loc[(df['いいね'] >= 50) & (df['いいね'] < 100), '等級'] = 'B'
    df.loc[(df['いいね'] >= 30) & (df['いいね'] < 50), '等級'] = 'C'
    df.loc[(df['いいね'] >= 10) & (df['いいね'] < 30), '等級'] = 'D'
    df.loc[df['いいね'] < 10, '等級'] = 'E'

    df['平均文字数'] = df['ツイート本文'].str.len()
    grouped_fav = df.groupby('等級')
    mean_word_df = grouped_fav.mean()[['平均文字数']]
    mean_word_df = mean_word_df.reset_index()

    hist_strnum_by_grade = alt.Chart(mean_word_df, title='等級と文字数の関係性').mark_bar().encode(
        x='等級',
        y='平均文字数',
        tooltip=['平均文字数']
    )
    return hist_strnum_by_grade


# 形態素解析による等級による普通名詞頻出度合い
def create_morphological_analysis(df, grade):
    wakati = MeCab.Tagger()

    _df = df[df['等級'] == grade]
    num_tweet = len(_df)

    txt = ' '.join(_df['ツイート本文'].to_list()).replace('https://t.co/', '')
    parts = wakati.parse(txt)

    words = []
    # 分かち書きより、普通名詞かつ2文字以上を抽出
    for part in parts.split('\n'):
        if '普通名詞' in part:
            word = part.split('\t')[0]
            if len(word) != 1:
                words.append(word)

    c = Counter(words)
    count_df = pd.DataFrame(c.most_common(30), columns=['単語', '出現回数'])

    bar2 = alt.Chart(count_df, title=f'{grade}評価の頻出単語 ツイート数{num_tweet}').mark_bar().encode(
        alt.X('出現回数:Q'),
        # y=alt.Y('単語:N', sort='-x')
        # 上記コードの場合、Streamlitで降順にならないため下記へ変更
        alt.Y('単語:N', sort=alt.EncodingSortField(field='出現回数', op='count', order='ascending'))
    )

    text = bar2.mark_text(
        align='left',
        baseline='middle',
        dx=3,
        color='gray'
    ).encode(
        text='出現回数:Q'
    )
    return bar2, text


def main():
    st.set_page_config(layout="wide")  # ワイドモードで表示
    st.title('Twitter データ解析')

    st.write('1. 分析用CSVファイルを用意してください（未取得の場合は別ページ参照）')

    st.write('2. 分析用CSVファイルをアップロードしてください')
    uploaded_file = st.file_uploader(' ', type=['csv'])
    if uploaded_file is not None:
        st.success('アップロードが完了しました')
        df = prepare_df(uploaded_file)

        col_L, col_R = st.columns(2)
        with col_L:
            st.write('2. いいね数ヒストグラム')
            hist1 = creat_hist_like(df)
            st.altair_chart(hist1, use_container_width=True)

        with col_L:
            st.write('3. 時間帯ごとの傾向')
            bar1, line = create_trend_by_time(df)
            st.altair_chart(bar1 + line, use_container_width=True)

        with col_L:
            st.write('4. 等級と文字数ヒストグラム')
            hist2 = create_hist_strnum_by_grade(df)
            st.altair_chart(hist2, use_container_width=True)

        with col_R:
            st.write('5. 形態素解析')
            grade = st.selectbox('等級の選択', ('A', 'B', 'C', 'D', 'E'))
            bar2, text = create_morphological_analysis(df, grade)
            st.altair_chart(bar2 + text, use_container_width=True)


if __name__ == '__main__':
    main()
