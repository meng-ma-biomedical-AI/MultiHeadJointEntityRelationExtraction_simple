# -*- coding: utf-8 -*-

# @Author  : xmh
# @Time    : 2021/3/3 17:28
# @File    : trainer.py

"""
file description:：

"""
import sys
sys.path.append('/home/xieminghui/Projects/MultiHeadJointEntityRelationExtraction_simple/')  # 添加路径

import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm
from utils.config import Config, USE_CUDA
from modules.joint_model import JointModel
from data_loader.data_process import ModelDataPreparation
import math
import numpy as np
# if torch.cuda.is_available():
#     USE_CUDA = True


class Trainer:
    def __init__(self,
                 model,
                 config,
                 train_dataset=None,
                 dev_dataset=None,
                 test_dataset=None,
                 token2id=None
                 ):
        self.model = model
        self.train_dataset = train_dataset
        self.dev_dataset = dev_dataset
        self.test_dataset = test_dataset
        self.config = config
        self.token2id = token2id
        
        # 初始优化器
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=config.lr)
        # 学习率调控
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, factor=0.5,
                                                                   patience=3, min_lr=1e-6, verbose=True)
        if USE_CUDA:
            self.model = self.model.cuda()
            
        self.num_sample_total = len(train_loader) * self.config.batch_size

        self.get_id2rel()

    def get_id2rel(self):
        self.id2rel = {}
        for i, rel in enumerate(self.config.relations):
            self.id2rel[i] = rel
        self.id2token_type = {}
        for i, token_type in enumerate(self.config.token_types):
            self.id2token_type[i] = token_type
        
    def train(self):
        print('STARTING TRAIN...')
        for epoch in range(self.config.epochs):
            print("Epoch: {}".format(epoch))
            # print(len(self.train_dataset))
            pbar = tqdm(enumerate(self.train_dataset), total=len(self.train_dataset))
            loss_total, loss_ner_total, loss_rel_total = 0, 0, 0
            # first = True
            # print("haha1")
            for i, data_item in pbar:
                # print("haha2")
                loss_ner, loss_rel, pred_ner, pred_rel = self.train_batch(data_item)
                # print("haha3")
                loss_total += (loss_ner + loss_rel)
                loss_ner_total += loss_ner
                loss_rel_total += loss_rel
                # if epoch % 5 == 0 and first:
                #     tmp_rel = pred_rel.numpy()
                #     # tmp_ner = pred_ner.numpy()
                #     cnt = 0
                #     for i in range(tmp_rel.shape[0]):
                #         for j in range(tmp_rel.shape[1]):
                #             for k in range(tmp_rel.shape[2]):
                #                 if tmp_rel[i,j,k,0] - 1.0 < 0.01 or 1.0 - tmp_rel[i,j,k,0] < 0.01:
                #                     cnt += 1
                #     print("共有{}个关系不是0".format(cnt))
                #
                #     np.savetxt("pred_rel.txt", tmp_rel.reshape(pred_rel.shape[0], -1))
                    # np.savetxt("pred_ner.txt", tmp_ner.reshape(pred_rel.shape[0], -1))
                    # first = False
            if (epoch+1) % 1 == 0:
                self.predict_sample()
            print("train ner loss: {0}, rel loss: {1}".format(loss_ner_total/self.num_sample_total, loss_rel_total/self.num_sample_total))
            # pbar.set_description('TRAIN LOSS: {}'.format(loss_total/self.num_sample_total))
            if (epoch+1) % 1 == 0:
                self.evaluate()
            
    
    def train_batch(self, data_item):
        # print("haha4")
        self.optimizer.zero_grad()
        # self.loss_ner, self.loss_rel, self.pred_ner, self.pred_rel = self.model(data_item)
        # self.loss = self.loss_ner + self.loss_rel
        # self.loss.backward()
        # self.optimizer.step()
        # print("haha5")
        loss_ner, loss_rel, pred_ner, pred_rel = self.model(data_item)
        
        loss = (loss_ner + loss_rel*100)
        # print("hello3")
        loss.backward()
        # print("hello4")
        self.optimizer.step()
        
        return loss_ner, loss_rel, pred_ner, pred_rel
    
    def evaluate(self):
        print('STARTING EVALUATION...')
        self.model.train(False)
        pbar_dev = tqdm(enumerate(self.dev_dataset), total=len(self.dev_dataset))
        
        loss_total, loss_ner_total, loss_rel_total = 0, 0, 0
        for i, data_item in pbar_dev:
            loss_ner, loss_rel, pred_ner, pred_rel = self.model(data_item)
            loss_ner_total += loss_ner
            loss_rel_total += loss_rel
            # loss_total += (loss_ner + loss_rel)
        print("eval ner loss: {0}, rel loss: {1}".format(loss_ner_total, loss_rel_total))
        self.model.train(True)
        
        return loss_total / (len(self.dev_dataset) * 8)
    
    def predict(self):
        print('STARTING TESTING...')
        self.model.train(False)
        pbar = tqdm(enumerate(self.test_dataset), total=len(self.test_dataset))
        for i, data_item in pbar:
            pred_ner, pred_rel = self.model(data_item, is_test=True)
        print("TEST NER:")
        print(pred_ner)
        print("TEST REL:")
        print(pred_rel)
        self.model.train(True)

    def predict_sample(self):
        print('STARTING TESTING...')
        self.model.train(False)
        pbar = tqdm(enumerate(self.test_dataset), total=len(self.test_dataset))
        data_item0 = None
        for i, data_item in pbar:
            
            pred_ner, pred_rel = self.model(data_item, is_test=True)
        data_item0 = data_item
        pred_ner, pred_rel = pred_ner[0], pred_rel[0]
        pred_rel_list = []
        for i in range(pred_rel.shape[0]):
            for j in range(pred_rel.shape[1]):
                for k in range(pred_rel.shape[2]):
                    if math.fabs(pred_rel[i, j, k] - 1.0) < 0.1:
                        # print(i, j, k, self.id2rel[k])
                        if k != 0:
                            pred_rel_list.append([i, j, self.id2rel[k]])
        token_pred = []
        for i in pred_ner:
            token_pred.append(self.id2token_type[i])
        print("token_pred: {}".format(token_pred))
        print(data_item0['text'][0])
        print(data_item0['spo_list'][0])
        print("pred_rel_list: {}".format(pred_rel_list))
        self.model.train(True)
        subject_all, object_all, rel_all = self.convert2StandardOutput(data_item0, token_pred, pred_rel_list)
        print("Results:")
        print("主体： \n", subject_all)
        print("客体： \n", object_all)
        print("关系： \n", rel_all)
        
    def convert2StandardOutput(self, data_item, token_pred, pred_rel_list):
        subject_all, object_all, rel_all = [], [], []
        text = [c for c in data_item['text'][0]]
        for item in pred_rel_list:
            subject, object, rel = [], [], []
            s_start, o_start = item[0], item[1]
            if token_pred[s_start][0] != 'B' or token_pred[o_start][0] != 'B' or s_start > len(text) or o_start > len(text):
                continue
            subject.append(text[s_start])
            object.append(text[o_start])
            s_start += 1
            o_start += 1
            while s_start < len(text) and (token_pred[s_start][0] == 'I' ): # or token_pred[s_start][0] == 'B'
                subject.append(text[s_start])
                s_start += 1
            while o_start < len(text) and (token_pred[o_start][0] == 'I'): #  or token_pred[o_start][0] == 'B'
                object.append(text[o_start])
                o_start += 1
            subject_all.append(''.join(subject))
            object_all.append(''.join(object))
            rel_all.append(item[2])
        
        return subject_all, object_all, rel_all
            
        
if __name__ == '__main__':
    config = Config()
    model = JointModel(config)
    data_processor = ModelDataPreparation(config)
    train_loader, dev_loader, test_loader = data_processor.get_train_dev_data(
        '../data/train_data_small.json',
    '../data/dev_small.json',
    '../data/predict.json')
    # train_loader, dev_loader, test_loader = data_processor.get_train_dev_data('../data/train_data_small.json')
    trainer = Trainer(model, config, train_loader, dev_loader, test_loader, data_processor.token2id)
    trainer.train()