import pandas as pd
import numpy as np
import re
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import os

# .env ファイルのキーバリューを環境変数に展開
from dotenv import load_dotenv
load_dotenv()

DATA_TYPE_MONTHLY = 'monthly'
DATA_TYPE_DAILY = 'daily'
DATA_TYPE = DATA_TYPE_DAILY # DATA_TYPE_MONTHLY | DATA_TYPE_DAILY

CN_DATE = 'date' # 日付
CN_NAP_COUNT = 'nap_count' # 昼寝回数
CN_NAP_MINUTE = 'nap_minute' # 昼寝時間
CN_NIGHT_SLEEP_COUNT = 'night_sleep_count' # 夜寝回数
CN_NIGHT_SLEEP_MINUTE = 'night_sleep_minute' # 夜寝時間
CN_NIGHT_WAKEUP_COUNT = 'night_wakeup_count' # 夜に起きる回数
CN_NIGHT_WAKEUP_MINUTE = 'night_wakeup_minute' # 夜に起きている時間
CN_MILK_COUNT = 'milk_count' # ミルク回数
CN_MILK_ML = 'milk_ml' # ミルク量
CN_BREASTFEEDING_COUNT  = 'breastfeeding_count' # 授乳回数
CN_BREASTFEEDING_MINUTE = 'breastfeeding_minute' # 授乳時間
CN_BABY_FOOD_COUNT = 'baby_food_count' # 離乳食回数
CN_BABY_FOOD_MINUTE = 'baby_food_minute' # 離乳食時間
CN_AGE_OF_MONTH = 'age_of_month' # 月齢

# 誕生日
birth_date = datetime.datetime.strptime(os.getenv('BABY_BIRTH_DATE'), '%Y-%m-%d')

# データ読込
# TODO: Google Drive 上のファイルを読み込めるようにする
path = ''
if DATA_TYPE == DATA_TYPE_MONTHLY:
    path = './data/monthly'
elif DATA_TYPE == DATA_TYPE_DAILY:
    path =  './data/daily'

# 指定したディレクトリ下の .txt ファイル名一覧を取得
files = [_ for _ in os.listdir(path) if _.endswith(r'.txt')]
month_texts = []
for filename in files:
    f = open(f'{path}/{filename}', encoding='utf-8')
    data = f.read()
    month_texts.append(data)
    f.close()

# 対象項目
def check_item(text):
    if re.findall('起きる|寝る|母乳|ミルク|離乳食|搾母乳', text) and re.match(r'([01][0-9]|2[0-3]):[0-5][0-9]', text):
        return True
    return False

# 対象データをリスト化
def get_piyolog_all_items(month_texts):
    all_items = []

    for month_text in month_texts:
        # 改行で分割
        lines = month_text.splitlines()
        array = np.array(lines)

        day = ''
        for index, item in enumerate(array):

            # 日付取得（月次データ）
            if DATA_TYPE == DATA_TYPE_MONTHLY and item == '----------' and index < len(array) - 1:
                day = array[index + 1][:-3] # 曜日「（月）など」の末尾3文字を除く文字列を抽出
                day_date = datetime.datetime.strptime(day, '%Y/%m/%d')
            # 日付取得（日次データ）
            elif DATA_TYPE == DATA_TYPE_DAILY and index == 0:
                day = array[index][6:-3] # 【ぴよログ】の先頭6文字と曜日「（月）など」の末尾3文字を除く文字列を抽出
                day_date = datetime.datetime.strptime(day, '%Y/%m/%d')

            # 対象項目の場合
            if item != '' and check_item(item):
                # 空白で分割
                record = item.split()

                record_dt = datetime.datetime.strptime(day + ' ' + record[0], '%Y/%m/%d %H:%M')
                record_type = None
                record_subtype = record[1]
                record_value = None
                record_timespan = None

                if '寝る' in record_subtype:
                    record_type = '睡眠'

                if '起きる' in record_subtype:
                    record_type = '睡眠'

                if 'ミルク' in record_subtype or '搾母乳' in record_subtype:
                    record_type = '食事'
                    # 搾母乳も項目名はミルクにする
                    record_subtype = 'ミルク'
                    # 時間は10分固定にする
                    record_timespan = 10
                    # ミルク量
                    record_value = int(record[2].replace('ml', ''))

                if '母乳' in record_subtype:
                    record_type = '食事'
                    record_time = 0
                    # 授乳時間の合計を計算する
                    for r in record[2:]:
                        if '分' in r:
                            record_time += int(re.sub(r'左|右|分', '', r, 2)) # 「左」や「右」などの先頭1文字と「分」の末尾1文字を除外
                    record_timespan = record_time
                            
                # 記録
                all_items.append([day_date, record_dt, record_type, record_subtype, record_timespan, record_value])

    return all_items

df = pd.DataFrame(get_piyolog_all_items(month_texts),columns=[CN_DATE, '日時','分類','項目','時間','ミルク量'])

# 睡眠時間
s_sleep_timespan = df.query('分類=="睡眠"').sort_values('日時', ascending=False).日時.diff() * -1
s_sleep_timespan.name = '睡眠時間'
df = pd.concat([df, s_sleep_timespan], axis=1)

# 睡眠時間(timedelta)を分に直す
def sleeptime_to_minutes(x):
    return x.睡眠時間.seconds / 60
df['睡眠時間'] = df.apply(lambda x:sleeptime_to_minutes(x),axis=1)

# 時間帯
def replace_time_zone(x):
    # 7:00～19:00の間に寝たものは昼寝とする
    if x.日時.hour >= 7 and x.日時.hour <= 18:
        return '昼'
    else:
        return '夜'
        
df['時間帯'] = df.apply(lambda x:replace_time_zone(x),axis=1)

# 月齢
month_old_list = []
for i in range(0,10):
    month_old_list.append([birth_date + relativedelta(months=i+1),i])
    
def replace_month_old(x):
    for month_old in month_old_list:
        if x.date < month_old[0]:
            return month_old[1]
        
df[CN_AGE_OF_MONTH] = df.apply(lambda x:replace_month_old(x),axis=1)

# 1日の夜に起きている回数・時間
df_night_wakeup = df.query('項目=="起きる" and 時間帯=="夜"').groupby(CN_DATE).agg({'日時':'count', '睡眠時間':'sum'}).reset_index()
df_night_wakeup.columns = [CN_DATE,CN_NIGHT_WAKEUP_COUNT,CN_NIGHT_WAKEUP_MINUTE]

# 1日の昼寝回数・時間
df_nap = df.query('項目=="寝る" and 時間帯=="昼"').groupby(CN_DATE).agg({'日時':'count', '睡眠時間':'sum'}).reset_index()
df_nap.columns = [CN_DATE,CN_NAP_COUNT,CN_NAP_MINUTE]

# 1日の夜寝回数・時間
df_night_sleep = df.query('項目=="寝る" and 時間帯=="夜"').groupby(CN_DATE).agg({'日時':'count', '睡眠時間':'sum'}).reset_index()
df_night_sleep.columns = [CN_DATE,CN_NIGHT_SLEEP_COUNT,CN_NIGHT_SLEEP_MINUTE]

# 1日の食事回数
df_milk = df.query('項目=="ミルク"').groupby(CN_DATE).agg({'日時':'count', 'ミルク量':'sum'}).reset_index()
df_milk.columns = [CN_DATE,CN_MILK_COUNT,CN_MILK_ML]
df_mother_milk = df.query('項目=="母乳"').groupby(CN_DATE).agg({'日時':'count', '時間':'sum'}).reset_index()
df_mother_milk.columns = [CN_DATE,CN_BREASTFEEDING_COUNT,CN_BREASTFEEDING_MINUTE]
df_eat = df.query('項目=="離乳食"').groupby(CN_DATE).agg({'日時':'count', '時間':'sum'}).reset_index()
df_eat.columns = [CN_DATE,CN_BABY_FOOD_COUNT,CN_BABY_FOOD_MINUTE]

# 重複した日付を削除して全日付を取得
df = df[CN_DATE].drop_duplicates()

# 1日集計のdf結合
df_groupby_day = pd.merge(df, df_nap, on=CN_DATE, how='left')
df_groupby_day = pd.merge(df_groupby_day, df_night_sleep, on=CN_DATE, how='left')
df_groupby_day = pd.merge(df_groupby_day, df_night_wakeup, on=CN_DATE, how='left')
df_groupby_day = pd.merge(df_groupby_day, df_milk, on=CN_DATE, how='left')
df_groupby_day = pd.merge(df_groupby_day, df_mother_milk, on=CN_DATE, how='left')
df_groupby_day = pd.merge(df_groupby_day, df_eat, on=CN_DATE, how='left')

# 月齢列の追加
df_groupby_day[CN_AGE_OF_MONTH] = df_groupby_day.apply(lambda x:replace_month_old(x),axis=1)

# dfからpostgresqlにインサート
from sqlalchemy.engine.url import URL
from sqlalchemy.engine.create import create_engine

# DB の接続情報
url = URL.create(
    drivername='mysql+mysqlconnector',
    username=os.getenv('USERNAME'),
    password=os.getenv('PASSWORD'),
    host=os.getenv('HOST'),
    port=3306,
    database=os.getenv('DATABASE'),
)
ssl_args = {'ssl_ca': './certificates/planetscale/cert.pem'}

# DB に接続
engine = create_engine(url, connect_args=ssl_args)

# DB の stats テーブルに INSERT
df_groupby_day.to_sql('stats', con=engine, schema=None, if_exists='append', index=False)
