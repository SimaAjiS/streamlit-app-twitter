import json
from collections import Counter

import MeCab
import altair as alt
import pandas as pd
import streamlit as st
import tweepy

st.title('Twitter分析アプリ')
st.write('''
このアプリはTwitter APIを使った分析アプリです。\n
ユーザーのタイムラインを様々な角度から分析します。
''')

option = st.sidebar.selectbox(
    'オプション',
    ['API認証とデータ取得', 'データ分析']
)

if option == 'API認証とデータ取得':
    uploaded_file = st.file_uploader('認証JSONファイルをアップロード', type=['json'])
    if uploaded_file is not None:
        auth_info = json.load(uploaded_file)
        consumer_key, access_token, access_token, access_token_secret, bearer_token = auth_info.values()

        client = tweepy.Client(bearer_token=bearer_token)
        st.write('認証が完了しました')

        # User IDの取得
        user_name = st.text_input('ユーザー名を入力して下さい', '03Imanyu')
        user_id = client.get_user(username=user_name).data.id

        st.write('### パラメータの設定')
        num_search_tweet = st.slider('検索件数', 10, 1000, 50)

        if st.button('データ取得'):
            message = st.empty()
            message.write("取得中...")

            columns = ['時間', 'ツイート本文', 'いいね', 'リツイート', 'ID']
            excludes = ['retweets', 'replies']
            tweet_fields = ['created_at', 'public_metrics']

            data = []
            for tweet in tweepy.Paginator(client.get_users_tweets, user_id, exclude=excludes,
                                          tweet_fields=tweet_fields).flatten(
                limit=num_search_tweet):
                text, _id, public_metrics, created_at = tweet['text'], tweet['id'], tweet['public_metrics'], tweet[
                    'created_at']
                datum = [created_at, text, public_metrics['like_count'], public_metrics['retweet_count'], _id]
                data.append(datum)

            df = pd.DataFrame(data=data, columns=columns)
            csv = df.to_csv(index=False).encode('utf-8')

            message.success('CSVファイルの出力が完成しました')
            st.download_button(
                label='CSVファイルをダウンロード',
                data=csv,
                file_name='../twitter_data.csv',
                mime='text/csv'
            )
            st.dataframe(df)

if option == 'データ分析':
    uploaded_file = st.file_uploader('分析用CSVファイルをアップロード', type=['csv'])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df['時間'] = pd.to_datetime(df['時間'])
        df['時間'] = df['時間'].dt.tz_convert('Asia/Tokyo')
        df['時刻'] = df['時間'].dt.hour

        # ヒストグラム
        hist1 = alt.Chart(df, title="いいね数の傾向").mark_bar().encode(
            alt.X('いいね', bin=alt.Bin(extent=[0, df['いいね'].max()], step=4), title='いいね数'),
            alt.Y('count()', title='回数'),
            tooltip=['count()']
        )
        st.altair_chart(hist1, use_container_width=True)

        # 時間帯ごとの傾向
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

        base = alt.Chart(result, title='時間帯ごとの傾向').encode(x='時刻:O')
        bar1 = base.mark_bar().encode(y='平均いいね数:Q', tooltip=['平均いいね数'])
        line = base.mark_line(color='blue').encode(y='ツイート数:Q', tooltip=['ツイート数'])

        st.altair_chart(bar1 + line, use_container_width=True)

        # 等級と文字数の関係
        df.loc[df['いいね'] >= 100, '等級'] = 'A'
        df.loc[(df['いいね'] >= 50) & (df['いいね'] < 100), '等級'] = 'B'
        df.loc[(df['いいね'] >= 30) & (df['いいね'] < 50), '等級'] = 'C'
        df.loc[(df['いいね'] >= 10) & (df['いいね'] < 30), '等級'] = 'D'
        df.loc[df['いいね'] < 10, '等級'] = 'E'

        df['平均文字数'] = df['ツイート本文'].str.len()
        grouped_fav = df.groupby('等級')
        mean_word_df = grouped_fav.mean()[['平均文字数']]
        mean_word_df = mean_word_df.reset_index()

        hist2 = alt.Chart(mean_word_df, title='等級と文字数の関係性').mark_bar().encode(
            x='等級',
            y='平均文字数',
            tooltip=['平均文字数']
        )

        st.altair_chart(hist2, use_container_width=True)

        # 形態素解析
        wakati = MeCab.Tagger()
        grades = ['A', 'B', 'C', 'D', 'E']
        for grade in grades:
            _df = df[df['等級'] == grade]
            num_tweet = len(_df)

            txt = ' '.join(_df['ツイート本文'].to_list()).replace('https://t.co/', '')
            parts = wakati.parse(txt)

            words = []
            for part in parts.split('\n'):
                if '名詞' in part:
                    word = part.split('\t')[0]
                    words.append(word)

            c = Counter(words)
            count_df = pd.DataFrame(c.most_common(30), columns=['単語', '出現回数'])

            bar2 = alt.Chart(count_df, title=f'{grade}評価の頻出単語 ツイート数{num_tweet}').mark_bar().encode(
                x='出現回数:Q',
                y=alt.Y('単語:N', sort='-x')
            )

            text = bar2.mark_text(
                align='left',
                baseline='middle',
                dx=3
            ).encode(
                text='出現回数:Q'
            )
            st.altair_chart(bar2 + text, use_container_width=True)
