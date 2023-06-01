import warnings
warnings.simplefilter('ignore')

import gc
import re
from collections import defaultdict, Counter

import numpy as np
import pandas as pd
pd.set_option('display.max_columns', None)
from tqdm.auto import tqdm

df_prod = pd.read_csv('products_train.csv')
df_prod

df_sess = pd.read_csv('sessions_train.csv')
df_sess

df_test = pd.read_csv('sessions_test_task1.csv')
df_test

# list all columns of df_prod
df_prod.columns
# Index(['id', 'locale', 'title', 'price', 'brand', 'color', 'size', 'model',
#        'material', 'author', 'desc'],
#       dtype='object')

# --- data preprocess functions ---

# use mT5 model to generate sentence embeddings for each session
import torch
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
# from transformers import AutoConfig
# config = AutoConfig.from_pretrained("./google/mt5-small/config.json")

tokenizer = AutoTokenizer.from_pretrained("google/mt5-base")
model = AutoModelForSeq2SeqLM.from_pretrained("google/mt5-base")

model.to(device)

from sklearn.decomposition import PCA

# generate sentence embedding
def generate_sentence_embedding(text):
    # get sentence embedding
    input_ids = tokenizer.encode(text, return_tensors='pt').to(device)
    with torch.no_grad():
        embeddings = model.get_encoder()(input_ids).last_hidden_state.mean(dim=1)
    embeddings_np = embeddings.T
    return embeddings_np

# example
text = "This is an example sentence."
sentence_embedding = generate_sentence_embedding(text)
print(sentence_embedding)

# --- END of data preprocess functions---


# ---


# feature2: locale

# generate one-hot encoding for locale
locale_onehot = pd.get_dummies(df_prod['locale'])
locale_onehot

# convert locale_onehot to pytorch tensor
locale_onehot = torch.tensor(locale_onehot.values)
locale_onehot

# save locale_onehot to file
torch.save(locale_onehot, 'locale_onehot.pt')
# # load locale_onehot from file
# locale_onehot = torch.load('locale_onehot.pt')


# ---


# feature2 cross with other features

# pass


# ---


# feature3: title
# find all nan values in df_prod['title']
title_na = df_prod[df_prod['title'].isna()]
len(title_na)

# fill nan values with empty string
df_prod['title'] = df_prod['title'].fillna('')

# generate embeddings for all titles
title_embeddings = []
for title in tqdm(df_prod['title']):
    title_embeddings.append(generate_sentence_embedding(title))

title_embeddings = torch.stack(title_embeddings, dim=0)

# save title_embeddings to file
torch.save(title_embeddings, 'title_embeddings.pt')
# # load title_embeddings from file
# title_embeddings = torch.load('title_embeddings.pt')

# normalization

# squeeze title_embeddings
title_embeddings = title_embeddings.squeeze()

# compute the l2-norm of title_embeddings
title_embeddings_norm = torch.norm(title_embeddings, p=2, dim=1)

# normalize title_embeddings
title_embeddings = title_embeddings / title_embeddings_norm.unsqueeze(1)

# check sum of the squares of each column of title_embeddings
title_embeddings_sum = torch.sum(title_embeddings**2, dim=1)


# save title_embeddings_normalized to file
torch.save(title_embeddings, 'title_embeddings_normalized.pt')
# # load title_embeddings_normalized from file
# title_embeddings = torch.load('title_embeddings_normalized.pt')


# # Too Large Dataset
# # elements_per_tensor = 768
# # bytes_per_element = 4
# # num_tensors = 1550000
# # total_storage = num_tensors * elements_per_tensor * bytes_per_element
# # total_storage_gb = total_storage / (1024**3)
# # print(f"Total storage required: {total_storage_gb:.2f} GB")
# # Total storage required: 4.43 GB

# # reduce dimension for title embeddings
# pca = PCA(n_components=192)
# title_embeddings_pca = pca.fit_transform(np.squeeze(title_embeddings))


# ---


# feature4: price

# 1. discrete feature from price
# save price to file by pandas
df_prod['price'].to_csv('price.csv', index=False)

# load price from file by pandas
price = pd.read_csv('price.csv')
price

# plot the distribution of log(price+1) and save it to file
import matplotlib.pyplot as plt
plt.hist(df_prod['price'], bins=20)
plt.savefig('price_log_hist.png')

# count the number of 0 in price
price[price==0].count()

# count the number of nan in price
price.isna().sum()


# extract the id of rows in price that are outliers, i.e., price = 40000000.07 from price
price_outliers_id = price[price==40000000.07]
# drop the items with NaN values in price_outliers
price_outliers_id = price_outliers_id.dropna().index
price_outliers_id


# get the rest of the rows in price that are not outliers
price_inliers_id = price[price!=40000000.07]
# drop the items with NaN values in price_outliers
price_inliers_id = price_inliers_id.dropna().index
price_inliers_id


# use these indexes to get the corresponding rows in df_prod
price_outliers = price.iloc[price_outliers_id]
price_inliers = price.iloc[price_inliers_id]


# separate price_inliers into 20 bins with equal frequency
price_bins = pd.qcut(price_inliers['price'], 20)


# get the categories of Series price_bins
price_bins_list = price_bins.cat.categories.tolist()
# add one new bin to price_bins for price_outliers representing [3933800, 40000000.07]
price_bins_list.append(pd.Interval(left=3933800.0, right=40000000.07, closed='right'))

# convert price_bins_list to intervalIndex
price_bins_cat = pd.IntervalIndex(pd.Categorical(price_bins_list, ordered=True))


# use price_bins_cat to allocate a new feature to price
# this feature means item belongs to which bin according to the value of price['price']
price['price_bin'] = price['price'].apply(lambda x: price_bins_cat.get_loc(x))


# find a value is in which bin of price_bins_cat
price_bins_cat.get_loc(40000000.07)

# save price to file
price.to_csv('price_discrete.csv', index=False)
# # load price from file
# price_discrete = pd.read_csv('price_discrete.csv')


# 2. continuous feature from price

# save price to file by pandas
df_prod['price'].to_csv('price.csv', index=False)

# load price from file by pandas
price = pd.read_csv('price.csv')
price

# get log(price+1) from price
price['price_log'] = np.log(price['price']+1)

# save price to file
price.to_csv('price_continuous.csv', index=False)
# # load price from file
# price_continuous = pd.read_csv('price_continuous.csv')


# merge price_discrete and price_continuous to a new dataframe price_all
price_all = pd.DataFrame()
price_all['price_discrete'] = price_discrete['price_bin']
price_all['price_continuous'] = price_continuous['price_log']

# convert price_all to tensor
price_all = torch.tensor(price_all.values, dtype=torch.float32)
# save price_all to file
torch.save(price_all, 'price_all.pt')
# # load price_all from file
# price_all = torch.load('price_all.pt')


# ---


# feature5: brand


# ---


# feature6: color


# ---


# feature7: size

# get all sizes from df_prod['size']
sizes = df_prod['size'].unique()
len(sizes)


# ---


# feature8: model


# ---


# feature9: material


# ---


# feature10: author


# ---


# feature11: desc / same to feature3
# find all nan values in df_prod['desc']
desc_na = df_prod[df_prod['desc'].isna()]
len(desc_na)

# fill nan values with empty string
df_prod['desc'] = df_prod['desc'].fillna('')

# generate embeddings for all descs
desc_embeddings = []
# test_descs = df_prod['desc'][:200]
# for desc in tqdm(test_descs):
for desc in tqdm(df_prod['desc']):
    desc_embeddings.append(generate_sentence_embedding(desc))

desc_embeddings = torch.stack(desc_embeddings, dim=0)

# save desc_embeddings to file
torch.save(desc_embeddings, 'desc_embeddings.pt')
# # load desc_embeddings from file
# desc_embeddings = torch.load('desc_embeddings.pt')


# normalization

# squeeze desc_embeddings
desc_embeddings = desc_embeddings.squeeze()

# compute the l2-norm of desc_embeddings
desc_embeddings_norm = torch.norm(desc_embeddings, p=2, dim=1)

# normalize desc_embeddings
desc_embeddings = desc_embeddings / desc_embeddings_norm.unsqueeze(1)

# check sum of the squares of each column of desc_embeddings
desc_embeddings_sum = torch.sum(desc_embeddings**2, dim=1)

# save desc_embeddings_normalized to file
torch.save(desc_embeddings, 'desc_embeddings_normalized.pt')
# # load desc_embeddings_normalized from file
# desc_embeddings = torch.load('desc_embeddings_normalized.pt')



# calculate the similarity between two embeddings for test set
# concat the tensors, i.e., price_all, title_embeddings, desc_embeddings to a new tensor in dim=0
locale_onehot = locale_onehot.to(device)
price_all = price_all.to(device)
feature_tensor = torch.cat((locale_onehot, price_all, title_embeddings, desc_embeddings), dim=1)

# save feature_tensor to file
torch.save(feature_tensor, 'feature_tensor.pt')
# # load feature_tensor from file
# feature_tensor = torch.load('feature_tensor.pt')






# count the number of nan in df_prod for each feature
df_prod.isna().sum()
# set weights for each feature according to the number of NaN values


def str2list(x):
    x = x.replace('[', '').replace(']', '').replace("'", '').replace('\n', ' ').replace('\r', ' ')
    l = [i for i in x.split() if i]
    return l

df_sess['prev_items_list'] = df_sess['prev_items'].apply(lambda x: str2list(x))

df_sess['prev_items_list'].apply(lambda x: len(x)).max() # maxlen: 474


# make a map from item to its feature tensor
# to fasten search the corresponding feature tensor
item2feature = {}
for i, row in tqdm(df_prod.iterrows(), total=len(df_prod)):
    # get numpy array of feature tensor feature_tensor[i]
    item2feature[str(row['id']) + ' ' + str(row['locale'])] = feature_tensor[i].cpu().numpy()



def get_feature(item, locale):
    # find feature tensor for feature_tensor
    feature = item2feature[item + ' ' + locale]
    return feature


def get_feature_list(prev_items_list, locale):
    feature_list = []
    for item in prev_items_list:
        feature_list.append(get_feature(item, locale))
    return feature_list



# get the corresponding feature tensors for prev_items_list in df_sess according to their id & locale
# df_sess['feature_list'] = df_sess.apply(lambda x: get_feature_list(x['prev_items_list'], x['locale']), axis=1)

# make a new column 'feature_list' in df_sess
df_sess['feature_list'] = None

# fully read: too slow

# for _, row in tqdm(df_sess.iterrows(), total=len(df_sess)):
#     row['feature_list'] = get_feature_list(row['prev_items_list'], row['locale'])
#     print(row['feature_list'])
#     df_sess.to_pickle('df_sess_feature_list'+'.pkl')


# to fasten read process
# read and save df_sess['feature_list'] to file by pickle
# separate df_sess['feature_list'] into 20 parts
part_len = len(df_sess) // 20
for i in range(20):
    df_sess_part = df_sess.iloc[i*part_len:(i+1)*part_len]
    for _, row in tqdm(df_sess_part.iterrows(), total=len(df_sess_part)):
        row['feature_list'] = get_feature_list(row['prev_items_list'], row['locale'])
        # print(row['feature_list'])
    # df_sess_part['feature_list'] = df_sess_part.apply(lambda x: get_feature_list(x['prev_items_list'], x['locale']), axis=1)
    df_sess_part.to_pickle('df_sess_part'+str(i)+'.pkl')


# get total train data
df_sess['total_feature_list'] = None

def get_total_feature_list(prev_items_list, next_item, locale):
    feature_list = []
    for item in prev_items_list:
        feature_list.append(get_feature(item, locale))
    feature_list.append(get_feature(next_item, locale))
    return feature_list

part_len = len(df_sess) // 20
for i in range(20):
    df_sess_part = df_sess.iloc[i*part_len:(i+1)*part_len]
    for _, row in tqdm(df_sess_part.iterrows(), total=len(df_sess_part)):
        row['total_feature_list'] = get_total_feature_list(row['prev_items_list'], row['next_item'], row['locale'])
    df_sess_part['total_feature_list'].to_pickle('df_sess_tot_feature'+str(i)+'.pkl')


# load df_sess['total_feature_list'] from file by pickle
for i in range(20):
    df_sess_part = pd.read_pickle('df_sess_tot_feature'+str(i)+'.pkl')

# convert df_sess_part['total_feature_list'] to tensor
feature_tensor_list = df_sess_part.apply(lambda x: np.array(x)).apply(lambda x: torch.from_numpy(x))




