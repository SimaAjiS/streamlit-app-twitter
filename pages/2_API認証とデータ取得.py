import json

import pandas as pd
import streamlit as st
import tweepy

# ワイドモードで表示
st.set_page_config(layout="wide")
st.title('Twitter API認証とデータ取得')

st.write('1. Twitter API 2.0用の認証キーを用意下さい')
st.write('2. 下記の内容をJSON形式で各自のローカル環境に保存します')

code = '''
{
    "consumer_key": "ABC123",
    "consumer_secret": "DEF456", 
    "access_token": "GHI789",
    "access_token_secret": "JKL101112",
    "bearer_token": "MNO131415"
}
'''
st.code(code, language='json')
st.write('3. ローカルに保存した認証用JSONファイルを下記へ読み込ませます')

uploaded_file = st.file_uploader('', type=['json'])
if uploaded_file is not None:
    auth_info = json.load(uploaded_file)
    consumer_key, access_token, access_token, access_token_secret, bearer_token = auth_info.values()

    client = tweepy.Client(bearer_token=bearer_token)
    st.success('認証が完了しました')

if uploaded_file is not None:
    st.write('4. データを取得するTwitterユーザー名を入力して下さい')
    user_name = st.text_input(' ', '03Imanyu')
    user_id = client.get_user(username=user_name).data.id

    st.write('5. データ検索件数を設定します')
    num_search_tweet = st.slider('検索件数', 10, 1000, 100)

    message = st.empty()
    if message.button('データ取得'):
        message.write("取得中...")

        # 除外項目、取得項目の設定
        excludes = ['retweets', 'replies']
        tweet_fields = ['created_at', 'public_metrics']

        data = []
        for tweet in tweepy.Paginator(
                client.get_users_tweets,
                user_id, exclude=excludes,
                tweet_fields=tweet_fields).flatten(limit=num_search_tweet):
            datum = {
                '時間': tweet['created_at'],
                'ツイート本文': tweet['text'],
                'いいね': tweet['public_metrics']['like_count'],
                'リツイート': tweet['public_metrics']['retweet_count'],
                'ID': tweet['id'],
                'url': f'https://twitter.com/{user_name}/status/{tweet["id"]}'
            }
            data.append(datum)
        df = pd.DataFrame(data)
        # いいね数降順にソートしておく
        df = df.sort_values(by='いいね', ascending=False)
        csv = df.to_csv(index=False).encode('utf-8')

        st.write('6. CSVファイルをローカル環境へ保存します')
        st.download_button(
            label='CSVファイルをダウンロード',
            data=csv,
            file_name='../twitter_data.csv',
            mime='text/csv'
        )
        message.success('CSVファイルの出力が完成しました')


        # url列をクリックできるリンクとして表示
        def make_clickable(url):
            return f'<a target="_blank" href="{url}">{url}</a>'


        st.write('7. データフレームの表示')
        df['url'] = df['url'].apply(make_clickable)
        st.write(df.to_html(escape=False), unsafe_allow_html=True)
        # st.dataframe(df)
