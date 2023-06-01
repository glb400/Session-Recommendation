import warnings
warnings.simplefilter('ignore')

import gc
import re
from collections import defaultdict, Counter

import numpy as np
import pandas as pd
pd.set_option('display.max_columns', None)
from tqdm.auto import tqdm


# df_prod = pd.read_csv('products_train.csv')
# df_prod

df_sess = pd.read_csv('sessions_train.csv')
df_sess


df_test = pd.read_csv('sessions_test_task1_phase2.csv')
df_test

# # get first line of df_sess
# df_sess.iloc[0]

def str2list(x):
    x = x.replace('[', '').replace(']', '').replace("'", '').replace('\n', ' ').replace('\r', ' ')
    l = [i for i in x.split() if i]
    return l


# next_item_dict：存储用户session商品中所有的next关系
next_item_dict = defaultdict(list)

# 遍历存储所有的next关系
for _, row in tqdm(df_sess.iterrows(), total=len(df_sess)):
    prev_items = str2list(row['prev_items'])
    next_item = row['next_item']
    prev_items_length = len(prev_items)
    if prev_items_length <= 1:
        next_item_dict[prev_items[0]].append(next_item)
    else:
        for i, item in enumerate(prev_items[:-1]):
            next_item_dict[item].append(prev_items[i+1])
        next_item_dict[prev_items[-1]].append(next_item)

for _, row in tqdm(df_test.iterrows(), total=len(df_test)):
    prev_items = str2list(row['prev_items'])
    prev_items_length = len(prev_items)
    if prev_items_length <= 1:
        continue
    else:
        for i, item in enumerate(prev_items[:-1]):
            next_item_dict[item].append(prev_items[i+1])

# 统计各商品后next出现的各商品次数
# 将出现次数最多的100个商品作为预测结果存入next_item_map

next_item_map = {}

for item in tqdm(next_item_dict):
    counter = Counter(next_item_dict[item])
    next_item_map[item] = [i[0] for i in counter.most_common(100)]

# 将next_item_dict的统计结果按返回形式存入df_next

k = []
v = []

for item in next_item_dict:
    k.append(item)
    v.append(next_item_dict[item])


df_next = pd.DataFrame({'item': k, 'next_item': v})
df_next = df_next.explode('next_item').reset_index(drop=True)
df_next

# 找出最常作为next出现的200个商品ID

top200 = df_next['next_item'].value_counts().index.tolist()[:200]

# 找出测试集session的最后一个商品ID并根据next_item_map查表预测

df_test['last_item'] = df_test['prev_items'].apply(lambda x: str2list(x)[-1])
df_test['next_item_prediction'] = df_test['last_item'].map(next_item_map)
df_test


# # 计算每个session中已经交互过的商品出现次数并将出现次数前10的商品ID作为预测结果存入next_item_prediction
# df_test['prev_items_list'] = df_test['prev_items'].apply(str2list)
# # count the number of each item in each session
# df_test['prev_items_list'].apply(Counter).head()
# # add the top 10 common items in each session into next_item_prediction
# df_test['next_item_prediction'] = df_test['next_item_prediction'] + df_test['prev_items_list'].apply(lambda x: [i[0] for i in Counter(x).most_common(10)])
# df_test


# 若预测结果为空，则取top200中的商品前100个
# 若预测结果不足100个，则将top200中的商品按顺序填充至100个（除去重复和已交互商品）

preds = []

for _, row in tqdm(df_test.iterrows(), total=len(df_test)):
    pred_orig = row['next_item_prediction']
    pred = pred_orig
    prev_items = str2list(row['prev_items'])
    if type(pred) == float:
        pred = top200[:100]
    else:
        if len(pred_orig) < 100:
            for i in top200:
                if i not in pred_orig and i not in prev_items:
                    pred.append(i)
                if len(pred) >= 100:
                    break
        else:
            pred = pred[:100]
    preds.append(pred)


df_test['next_item_prediction'] = preds
df_test

df_test['next_item_prediction'].apply(len).describe()

# df_test[['locale', 'next_item_prediction']].to_parquet('rule_recall_test.parquet', engine='pyarrow')

# save df_test[['locale', 'next_item_prediction']] into pickle
df_test[['locale', 'next_item_prediction']].to_pickle('history_rule_recall_100_test.pkl')
# # load df_test[['locale', 'next_item_prediction']] from pickle
# df_test = pd.read_pickle('history_rule_recall_100_test.pkl')

