# -*- coding: utf-8 -*-

from response import myResponse
from bs4 import BeautifulSoup
import time, datetime
import math
import re
import threading  # 用于多线程工作
import pickle
import requests
import json
from dateutil import parser as dateParser
import urllib3
from emailserver import sendEmail
import utils

# 禁用安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TBaiDuNewsScapper:
    __Author__ = 'xiaoyuan'
    Master = {'Master':{'UserName':'', 'NickName':'xiaoyuan'}}
    initNewsinList = 100
    maxNewsinList = 2000
    maxUserNum = 5
    # NewsList 仅能在初始化或者发送提醒消息后更改，切记！
    extMsg = '百度新闻实时监控下线，管理员正在处理。有急事请联系管理员：18810181988！'
    label = ' # 百度新闻实时监控程序 # '
    newsNumpPage = 20
    maximumNews2Get = 300

    souGou_Thresh = 0
    souGou_WeChat = 0
    souGou_RestTime = 180 # min
    def __init__(self,callName, nickName, mhotReload):
        """
        初始化NewsList的新闻信息
        """
        #-----------------实例不共享变量定义----------------------#
        self.mainUser  = callName # store the keyname or call name of the class
        self.pricklefileName = utils.pickle_dir + self.mainUser + '_News_热启动文件.pickle'
        self.logfile = utils.log_dir + self.mainUser + '_BaiDuNews.log'
        self.mu =  threading.RLock()
        self.f = open(self.logfile,'a+')
        self.ResSetFlag = False
        # 初始化管理员账号
        # try:
        #     WeChat.InitWeChatUsers(self.Master, self.logfile) # 热启动后用户名会发生改变
        # except Exception as e:  # 异常，向上抛出。如果第一次初始化，属于严重异常，创建列表中初始化，属于一般异常
        #     errmsg = '新闻监控类管理员账号初始化异常: ' + str(e)
        #     self.write2Log(errmsg)
        #     print(errmsg)
        #     raise Exception(errmsg)
        utils.getSendSuccessNews()
        # 添加用户列表，并进行初始化 
        hotReload = False
        if mhotReload:
            hotReload, data = self.getDatafromPickle(self.pricklefileName)
        if mhotReload and hotReload: # 同时满足才热启动
            # self.UserList = data['UserList']
            self.keywordList = data['keywordList']
            if 'subkeywordList' in data:
                self.subkeywordList = data['subkeywordList']
            else:
                for key in self.keywordList:
                    self.subkeywordList.setdefault(key, set())
            if 'serachRangeOpts' in data:
                self.serachRangeOpts = data['serachRangeOpts']
            else:
                self.serachRangeOpts = {}
                for key in self.keywordList:
                    self.serachRangeOpts[key] = {'百度新闻':True, '百度网页':False,'搜狗新闻':False,'搜狗微信':False,'今日头条':False }
            print(self.serachRangeOpts)
            self.companyInFiled = data['companyInFiled']
            self.numOfNewsInEachScan = data['numOfNewsInEachScan']
            self.numOfNewsInFieldComp = data['numOfNewsInFieldComp']
            self.defaultSortMethod = data['defaultSortMethod']
            self.residDays = data['residDays']
            self.NewsList = data['NewsList']
            self.initMsg = '百度新闻实时监控 by ' + str(self.__Author__) + ' 上线，监控关键词为： ' + str(self.keywordList) + '。'
            self.newsFileTail = data['newsFileTail']
            
            if 'souGou_Thresh' in data:
                self.souGou_Thresh = min(data['souGou_Thresh'], datetime.datetime.now().timestamp() + self.souGou_RestTime*60)
            else:
                self.souGou_Thresh = 0  
            if 'souGou_WeChat' in data:
                self.souGou_WeChat = min(data['souGou_WeChat'],datetime.datetime.now().timestamp() + self.souGou_RestTime*60)
            else:
                self.souGou_WeChat = 0       
            if 'souGou_RestTime' in data:
                self.souGou_RestTime = data['souGou_RestTime']  
            else:
                self.souGou_RestTime = 180                     
            # log file
            # try:
            #     WeChat.InitWeChatUsers(self.UserList, self.logfile) #初始化用户账号
            # except Exception as e:   #异常，向上抛出。如果第一次初始化，属于严重异常，创建列表中初始化，属于一般异常
            #     errmsg = '新闻监控类用户列表初始化异常: ' + str(e) + '。已通知管理员处理！'
            #     self.write2Log(errmsg)
            #     self.SendAlert2Master(str(self.label) + str(errmsg))
            #     print(errmsg)
            #     raise Exception(errmsg)
        else:
            # self.UserList = {}  #第一个默认为主账号，其余为副账号
            self.keywordList = ['高科技'] # 每次更新keyswords时，需要同步更新residDays
            self.subkeywordList = {self.keywordList[0]:set(['全球'])} # 副标签的作用是，每个关键词可以依次循环搜索副关键词，并查询其新闻内容；每个新闻中，应该在标题或者摘要中包含至少一个主关键词或者副关键词，否则认为是垃圾信息
            self.serachRangeOpts = {self.keywordList[0]:{'百度新闻':True, '百度网页':False,'搜狗新闻':False,'搜狗微信':False,'今日头条':False }}
            self.companyInFiled = ['全球']
            self.numOfNewsInEachScan = 60
            self.numOfNewsInFieldComp = 60
            self.defaultSortMethod = 'date'
            self.residDays = dict.fromkeys(self.keywordList,365)
            self.NewsList = {} # 是个字典，每个关键词对应一个列表。列表中最多200条新闻。每次更新时，更新列表信息。列表本质是排序的
            self.initMsg = '百度新闻实时监控 by ' + str(self.__Author__) + ' 上线，监控关键词为： ' + str(self.keywordList) + '。'
            self.newsFileTail = '_' + self.mainUser + '_newsList.txt'
            self.ResSetFlag = False
            self.souGou_Thresh = 0  
            self.souGou_WeChat = 0       
            self.souGou_RestTime = 180              
            
            print(self.initMsg + ' 用户：' + str(callName))
            self.write2Log(self.initMsg  + ' 用户：' + str(callName))
        #-------------------变量定义结束------------------------#
            # 添加用户列表，并进行初始化    
            # try:
            #     self.UserList.setdefault(callName,{'UserName':'', 'NickName':nickName})  # 将主账户加入UserList
            #     WeChat.InitWeChatUsers(self.UserList, self.logfile) #初始化用户账号
            # except Exception as e:   #异常，向上抛出。如果第一次初始化，属于严重异常，创建列表中初始化，属于一般异常
            #     errmsg = '新闻监控类用户列表初始化异常: ' + str(e) + '。已通知管理员处理！'
            #     self.write2Log(errmsg)
            #     self.SendAlert2Master(str(self.label) + str(errmsg))
            #     print(errmsg)
            #     raise Exception(errmsg)
            # 检查关键词，并设置有效期
            if len(self.keywordList) < 1:
                with self.mu:    ##加锁
                    self.keywordList.append('互联网')
                    for keyword in self.keywordList:
                         self.residDays[keyword] = 365
            try: 
                print('初始化新闻列表中...\n')
                self.createNewsList()  # 以目前状态初始化新闻列表
            except Exception as e:  #异常，向上抛出。如果第一次初始化，属于严重异常，创建列表中初始化，属于一般异常
                errmsg = '新闻监控类新闻列表创建异常：' + str(e) + '，已通知管理员处理！'
                self.write2Log(errmsg)
                self.SendAlert2Master(str(self.label) + str(errmsg))
                print(errmsg)
                raise Exception(errmsg)
    def Run(self):
        with self.mu:
            # 扫描一次所有关键词，将更新结果返回
            print('开始一次 ' + str(self.label))
            msgcontent = ''
            # 反爬虫预警
            if datetime.datetime.now().timestamp() < self.souGou_Thresh:
                errMsg = '搜狗新闻平台遭遇反爬虫系统（' + self.mainUser + '），休息中！剩余时间：' +  str(math.floor((self.souGou_Thresh - datetime.datetime.now().timestamp())/60)) + ' 分钟！'  
                self.SendAlert2Master(str(errMsg))
            if datetime.datetime.now().timestamp() < self.souGou_WeChat:
                errMsg = '搜狗-微信公众号平台遭遇反爬虫系统（' + self.mainUser + '），休息中！剩余时间：' +  str(math.floor((self.souGou_WeChat - datetime.datetime.now().timestamp())/60)) + ' 分钟！' 
                self.SendAlert2Master(str(errMsg))   
            print(self.souGou_Thresh)
            print(self.souGou_WeChat)  
            print(self.souGou_RestTime)
            for keyword in self.keywordList:
                print('关键词 【' + keyword + '】')
                try:
                    # 每隔1小时，更新一次时间戳
                    now = int(datetime.datetime.now().timestamp())
                    if now % 3600 < 2:
                        print(self.label + ' 更新关键词时间戳：' + keyword)
                        self.NewsList[keyword] = self.updateDateStamp(self.NewsList[keyword])
                except Exception as e: # 如果更新时间戳出现异常，通知管理员，然后pass
                    errmsg = '# 更新时间戳异常，已通知管理员处理！' + str(e)
                    print(errmsg)
                    self.write2Log(errmsg)
    #                    WeChat.SendWeChatMsgToUserList(self.Master, errmsg, self.logfile)
                    self.SendAlert2Master(str(self.label) + str(errmsg))
                try:
                    # 扫描是否有新消息
                    updateFlag, updateMsg = self.scrapUpdatedNews(keyword)
                    if updateFlag:
                        print(self.label + ' 已经向用户email发送news：' + keyword)
                        msgcontent = msgcontent + updateMsg + '\n'
                        # WeChat.SendWeChatMsgToUserList(self.UserList, msgcontent, self.logfile)
                        sendEmail(msgcontent)
                    else:
                        print("news 不符合")
                except Exception as e: #一般错误
                    errmsg = '新闻监控类运行异常: # 更新监控列表失败: ' + str(e) + '， 已通知管理员处理！\n'
                    print(errmsg)
    #                    WeChat.SendWeChatMsgToUserList(self.Master, errmsg, self.logfile)
                    sendEmail(errmsg)
                    self.SendAlert2Master(str(self.label) + str(errmsg))
                    self.write2Log(errmsg)
                    # 向上抛出异常
                    raise Exception(errmsg)
            print('结束一次 ' + str(self.label))
    def pickleDump2file(self, filename):
        try:
            data = {}
            # data.setdefault('UserList',self.UserList)
            data.setdefault('keywordList',self.keywordList) 
            data.setdefault('subkeywordList',self.subkeywordList) 
            data.setdefault('serachRangeOpts',self.serachRangeOpts) 
            data.setdefault('souGou_Thresh',self.souGou_Thresh)
            data.setdefault('souGou_WeChat',self.souGou_WeChat)
            data.setdefault('souGou_RestTime',self.souGou_RestTime)
            data.setdefault('companyInFiled',self.companyInFiled) 
            data.setdefault('numOfNewsInEachScan',self.numOfNewsInEachScan) 
            data.setdefault('numOfNewsInFieldComp',self.numOfNewsInFieldComp) 
            data.setdefault('defaultSortMethod',self.defaultSortMethod) 
            data.setdefault('residDays',self.residDays) 
            data.setdefault('NewsList',self.NewsList) 
            data.setdefault('initMsg',self.initMsg) 
            data.setdefault('newsFileTail',self.newsFileTail) 
            # log file    
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
                print('新闻监控类：pickle file写入成功！')
                self.write2Log('新闻监控类：pickle file写入成功！')
        except Exception as e:
            print('新闻监控类：pickle file写入异常！' + str(e))
            self.write2Log('新闻监控类：pickle file写入异常！' + str(e))
    def getDatafromPickle(self,filename):
        Flag = False
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                Flag = True
                print('新闻监控类：pickle file读取成功！')
                self.write2Log('新闻监控类：pickle file读取成功！')
        except Exception as e:
            Flag = False
            data = '# 新闻监控类热启动失败！开始初始化：' + str(e)
            print(data)
            self.write2Log(data)
        return Flag, data
    def createNewsList(self):
        # 创建列表
        with self.mu:
            for keyword in self.keywordList:
                self.createNewsListofOneKeyword(keyword)
                
    def createNewsListofOneKeyword(self, keyword):
        # 创建列表
        succ, news = self.getNews( keyword, self.initNewsinList, self.defaultSortMethod)
        if succ:
            with self.mu:
                try:
                    self.NewsList.setdefault(keyword, news)
                    self.writeNews2File(self.NewsList[keyword], utils.news_dir + keyword + self.newsFileTail, '## 初始化关键词新闻列表 ##：【 ' + keyword + ' 】 最近 ' + str(self.initNewsinList) + ' 条新闻搜索结果如下（时间排序）：\n\n', 'w+')
                except Exception as e:
                    raise Exception('创建新闻列表异常：获取新闻失败！' + keyword)
    def getMainUser(self):
        return self.mainUser 
    def addNews2List(self, keyword, news):
        try:
            Output = ''
            if keyword in self.keywordList:
                # 仅在keyword存在时，才能使用此函数
                if len(self.NewsList[keyword]) < self.maxNewsinList:
                    self.NewsList[keyword].insert(0, news)
                else:
                    while len(self.NewsList[keyword]) > self.maxNewsinList:
                        self.NewsList[keyword].pop() # 删除最后一条
                    self.NewsList[keyword].insert(0, news) # 在最开始加入，默认为新来的总是最新发生的时间
                # 如果NewsList中尚未达到上限，直接加入，否则移除最后一条，并添加新的一条
                # 重新排序
                Output  = '## 更新关键词 【：' + keyword + ' 】 新闻列表成功！\n'
                self.writeNews2File(self.NewsList[keyword], utils.news_dir + keyword + self.newsFileTail, '## 更新关键词 【：' + keyword + ' 】 新闻列表， 最近 ' + str(len(self.NewsList[keyword])) + ' 条新闻搜索结果如下（时间排序）：\n\n','a+')
            else: # 一般错误
                # 否则，报错
                Output = '# 新闻列表添加错误： ' + keyword + '不在关键词列表中！' 
                self.SendAlert2Master(str(self.label) + str(Output))
        except Exception as e:
            errmsg = '添加新闻至列表异常：In addNews2List():' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(self.label) + str(errmsg))
            raise  Exception(errmsg)
        return Output
    def newsInList(self, keyword, news):
        # news 和 old news 是新闻的键值对，见addNews2List中说明
        # 如果找到，返回True，找不到，返回False
        findNews = False # 外部已经加锁
        with self.mu:
            for oldnews in self.NewsList[keyword]:
                if self.sameNews(oldnews[1], news[1]):
                    findNews = True
                    break
        return findNews


    def scrapUpdatedNews(self, keyword):
        # 扫描一个关键词，得到其前10条新闻列表。逐条判断该新闻是否在该关键词列表中
        # 如果在，返回false
        # 如果不在，返回新闻格式，并将其作为新的新闻返回
        update = False
        result = '\n检测到新的新闻 【 ' + keyword + ' 】：\n' 
        try:
            succ, news = self.getNews(keyword, self.numOfNewsInEachScan, self.defaultSortMethod) 
            # news是个键值对
            if not succ:
                self.SendAlert2Master(str(self.label) + str('警告管理员：新闻监控中关键词【' + keyword + ' 】 新闻获得失败！'))
                return False, result # 这里应该发警报
        except Exception as e: # 如果新闻列表获取错误，则直接返回
            update = False
            errmsg = 'scrapUpdatedNews(): 获取新闻列表失败：' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(self.label) + str(errmsg))
            return update, result
        # 此处得到的news是该keyword下，key排序后的列表
        try:  # Run已经锁定
            for newsitem in news:

                # 如果不是今日新闻，跳过
                # news 中已经排序
                body = newsitem[1] # 获得其键值，其下属有'标题',‘date'等
                now = datetime.datetime.now()

                # 剔除已经发送的标题
                title = body["title"]
                if len(title) == 0:
                    continue
                isSend = False
                for localNewsDict in utils.sendSuccessList:
                    localTitle = localNewsDict["title"]
                    if localTitle in title or title in localTitle or title is localNewsDict:
                        isSend = True
                        break
                if isSend == True:
                    continue

                recDay = 1
                FindNews =  False # 是否是最近3天新闻
                for i in range(recDay): # i = 0 ~ recDay - 1
                    day = now - datetime.timedelta(days = i)
                    # 抓取的时间可能是2018年08月29日
                    date = '%04d年%02d月%02d日'%(day.year, day.month, day.day)
                    # 抓取的时间可能是2018-08-29
                    date1 = '%04d-%02d-%02d' % (day.year, day.month, day.day)
                    dateInBody = body['date']
                    if date in dateInBody or date1 in dateInBody:
                       FindNews = True
                    elif "小时前" in dateInBody or "2天前" in dateInBody or "1天前": # dateInBody 中的内容是多少小时前
                        FindNews = True
                if not FindNews:
                    continue
                utils.sendSuccessList.append(body)
                # 暂时先不要逐条扫描
                result = result + self.printNews2Format(newsitem) + '\n'
                update = True
                # 添加新闻
                self.addNews2List(keyword, newsitem)
                # 逐条扫描
                # if not self.newsInList(keyword, newsitem):
                # # 如果该条新闻不在列表中，在result中追加该新闻列表
                #     result = result + self.printNews2Format(newsitem) + '\n'
                #     update = True
                #     # 添加新闻
                #     self.addNews2List(keyword, newsitem)
                # else:
                #     pass
                #     #print('news 过滤不符合')
        except Exception as e: #一般错误，如果出错，返回错误
            update = False
            errmsg = '刷新新闻异常：scrapUpdatedNews():' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(self.label) + str(errmsg))
            pass
        utils.syncNews2File()
        return update, result
    def printNews2Format(self, news):
        '''
         title = news["title"]
        author = news["author"]
        date = news["date"]
        link = news["link"]
        platform = news["platform"]
        source = news["source"]
        summary = news["summary"]
        timeflag = news["timeflag"]
        '''
        # new 格式是排序后的，见addNews2List
        Output = ''
        body = news[1]
        Output = Output + ("标题: " + body['title'] + "\n")
        source = body['author'] + '  ' + body['date'] + ''
        if not body['timeflag']:
            source = source + '(大约)'
        Output = Output + "来源: " + source + '（' + body['platform'] + '）\n' + "链接: " + body['link'] + "\n" + "简介: " + body['summary'] + "\n"      
        return Output
    def getFileName(self, keywords):
        return (utils.news_dir + keywords + '_newslist' + str(time.strftime('_%Y_%m_%d_%H_%M_%S', time.localtime(time.time()))) + '.txt')

    def write2Log(self, msg):
        try:
            if self.f.closed:
                self.f = open(self.logfile,'a+')
            self.f.write(msg + '\n')
            self.f.close()
        except Exception as e:
            errmsg = '# 新闻监控类写入日志异常：' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(self.label) + str(errmsg))
    def __del__(self):
        print('删除' + str(self.label))
    def Bye(self, Debug):
        if not Debug:
            self.pickleDump2file(self.pricklefileName)
        print(self.extMsg)
        sendEmail(self.extMsg)

    def OnDuty(self):
        return True #全时工作
    def SendAlert2Master(self, errmsg):
        pass
        # errmsg2 = '程序异常，提醒管理员：\n' + str(errmsg)
        # self.write2Log(str(self.label) + str(errmsg2))
        # WeChat.SendWeChatMsgToUserList(self.Master, errmsg2, self.logfile)
        # print(str(self.label) + str(errmsg2))
    def scrapNews(self, keywords, newsNum):
        Output_sum = {}
        succ = False
        # 每个Output的格式如下
        # 命名：'平台名_' + str(author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor))
        # title
        # source
        # author
        # date
        # time_flag
        # link
        # summary
        # platform
        # 先搜索其主关键词，如果有福关键词，也一并搜索
        # subkeywordList
        localKeyWord = set([keywords]) # 默认为主关键词
        if keywords in self.subkeywordList:
            localKeyWord = localKeyWord | self.subkeywordList[keywords] # 求并集
        # 循环搜寻主、副关键词新闻
        #self.serachRangeOpts[key]
        tempFlag = False
        if keywords not in self.serachRangeOpts:
            self.serachRangeOpts[keywords] = {'百度新闻':True, '百度网页':False,'搜狗新闻':True,'搜狗微信':False,'今日头条':True }
            tempFlag = True
        for a_keyWord in localKeyWord:
            Flag_BD = Flag_SG = Flag_SGWe = Flag_JRTT = FG_BDWeb = False
            if self.serachRangeOpts[keywords]['百度新闻']:
                Flag_BD, news = self.searchBaiDuNews(a_keyWord, newsNum)  # 百度新闻
                if Flag_BD:
                    Output_sum.update(news)
            if self.serachRangeOpts[keywords]['搜狗新闻']:
                Flag_SG, news = self.searchSouGouNews(a_keyWord, newsNum) # 搜狗新闻
                if Flag_SG:
                    Output_sum.update(news)
            if self.serachRangeOpts[keywords]['搜狗微信']:
                Flag_SGWe, news = self.searchSouGou_WeChatNews(a_keyWord, newsNum) # 搜狗-微信公众号
                if Flag_SGWe:
                    Output_sum.update(news)           
            if self.serachRangeOpts[keywords]['今日头条']:
                Flag_JRTT, news = self.searchJinRiTouTiao(a_keyWord, newsNum) # 今日头条
                if Flag_JRTT:
                    Output_sum.update(news) 
            if self.serachRangeOpts[keywords]['百度网页']:
                FG_BDWeb, news = self.searchBaiDuWeb(a_keyWord, newsNum) # 百度网页
                if FG_BDWeb:
                    Output_sum.update(news)         
            succ = succ or Flag_BD or Flag_SG or Flag_SGWe or Flag_JRTT or FG_BDWeb
        # Output 中去重（主副关键词搜索结果可能接近）
        
        if succ:
            new_output  = {}
            news_assemble = set()
            for news in Output_sum:
                tempvalues = new_output.values()
                if Output_sum[news] not in tempvalues: #去重(仅去除完全相同的新闻)
                    keysen = ['周末消息重磅来袭', '重磅利好', '重大利好消息', '节后重大利好消息', '最新消息利好',  '最新利好消息', '罕见利好消息', '特大利好强势来袭', '特大利好消息']
                    # kws = list(localKeyWord) # 将set强转为list 然后将其元素添加到需要过滤的列表中 xiaoyuan add
                    # keysen += kws
                    symbol = [' ', '、']
                    Flag = True
                    for key in keysen:
                        if key in Output_sum[news]['title']:
                            Flag = False
                    if '澳门' in Output_sum[news]['title'] and '赌城' in Output_sum[news]['title']:
                        Flag = False
                    if '澳门' in Output_sum[news]['title'] and '娱乐场' in Output_sum[news]['title']:
                        Flag = False    
                    if '华股财经' in Output_sum[news]['author']:
                        Flag = False
                    title = Output_sum[news]['title']
                    author = Output_sum[news]['author']
                    # for symb in symbol:
                    #     if title.count(symb) >= 3:
                    #         Flag = False
                    if (title + author) in news_assemble:
                        Flag = False
                    if Flag:
                        news_assemble.update(title + author)
                        new_output.setdefault(news, Output_sum[news])
        else:
            print(self.label + '抓取关键词 【' + str(keywords) + '】新闻失败！' )
            new_output  = {}
        if tempFlag:
            self.serachRangeOpts.pop(keywords) # 如果是临时搜索，则从列表中移除该变量

        if succ == False:
            pass
        return succ, new_output ## 字典形式的           
            
    def searchBaiDuNews(self, keywords, newsNum):
        Output = {} 
        newsPerPage = 20
        numOfPage = math.ceil(newsNum/newsPerPage)
        Countor = 0
        succ = False
        print('百度新闻平台搜索关键词：' + keywords)
        for k in range (0, numOfPage):
            url = 'http://news.baidu.com/ns?word=' + keywords + '&pn=%s&cl=2&ct=1&tn=news&rn=20&ie=utf-8&bt=0&et=0'% (k* newsPerPage)
            headers = {'User-Agent': utils.get_random_user_agent()}
            response = myResponse(url=url,headers=headers, encode = 'utf-8')
            soup = BeautifulSoup(response.text,'lxml')
            div_items = soup.find_all('div', class_ = 'result') # 获得 div标签下， class = 'result'的内容:即提取div； 在每个find函数中，第一个如’div'为标签，在html中总是成对出现的，第二个是标签后面跟的
            if len(div_items) < newsPerPage:
                numOfPage = k + 1
            
            for div in div_items:
                if Countor >= int(newsNum):
                    break
                Countor = Countor + 1
                # 去除title,连接
                try:
                    a_title = div.find('h3', class_='c-title').find('a').get_text() #获得 h3标签下，class为c-title的内容，然后在其中，获得a标签下的所有文本内容
                except Exception as e:
                    a_title = '标题解析错误'
                try:
                    a_href = div.find('h3', class_='c-title').find('a').get('href') # 获得链接
                except Exception as e:
                    a_href = '链接解析错误'
                try:
                    a_summary = div.find('div', class_='c-summary').get_text().replace(u'\xa0',u' ').replace(u'\u2022','·')     # 获得简介
                except Exception as e:
                    a_summary = '简介解析错误'
                try:
                    a_author = div.find('div', class_='c-summary').find('p', class_="c-author").get_text().replace(u'\xa0',u' ')
                    a_summary2 = a_summary[len(a_author): len(a_summary)] # 在summary中去掉 author信息
                except Exception as e:
                    a_author = '作者解析错误 日期解析错误 时间解析错误'
                    a_summary2 = a_summary
                
                # 拆分a_author
                source = str(a_author)
                source = source.split(' ')
                source = filter(lambda x: x != '',source) # 去除空元素
                source = filter(lambda  x: x != '\n', source) # 去除\n
                source = filter(lambda x: x != '\n\n', source)  # 去除\n\n
                source = [i for i in source]
                time_flag = False  # True： 准确时间， False，大约时间，需要在后续时间进行更新
                if len(source) == 2:
                    now = int(datetime.datetime.now().timestamp())
                    # 有种情况是作者不存在
                    author = source[0]
                    delta_time_str = source[1]
                    if ('年' in author and '月' in author and '日' in author) or '分钟' in author or '小时' in author:
                        # 这种情况下，一般是author不存在
                        author = '无名氏'
                        author_date  = source[1] + ' ' + source[2]
                        time_flag = True
                        succ = True
                        # 如果作者不存在，则分钟或小时形式的不存在，因为那样的话，len(source) = 1
                    else: # 作者存在
                        delta_time = 0
                        if '分钟' in delta_time_str:
                            delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                        elif '小时' in delta_time_str:
                            delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                        else:
                            print('str is  ' + delta_time_str)
                            delta_time = 0
                            errmsg = 'In searchBaiDuNews(): # Error: in scrapper news, analysis of the news time failed: ' + str(source) # (其他情况，delta_time置为0，即认为是现在发生的)
                        author_time_format = time.localtime(now - delta_time)
                        author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                        succ = True
                elif len(source) == 3:
                    time_flag = True
                    author = source[0]
                    author_date = source[1] + ' ' + source[2]
                    succ = True
                elif len(source) ==  1:
                     # 作者不存在（时间为小时或者分钟形式）或者时间不存在（仅为作者）
                     if '分钟' in source[0] or '小时' in source[0]:
                         # 无作者
                         author = '无名氏'                       
                         now = int(datetime.datetime.now().timestamp())
                         # 有种情况是作者不存在
                         delta_time_str = source[0]
                         delta_time = 0
                         if '分钟' in delta_time_str:
                             delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                         else:
                             delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                         author_time_format = time.localtime(now - delta_time)
                         author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                     else: # 时间不存在
                         author = source[0]
                         now = time.localtime() # 将现在置为其准确时间
                         author_date = '%04d年%02d月%02d日 %02d:%02d'%(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min)
                         time_flag = True
                     succ = True
                else: 
                    errmsg = '未发现新闻:' +  str(source)
                    print(str(errmsg))
                    continue
                # 新建字典
                temptime = datetime.datetime.now()
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary2 + '\n')
                    continue  
                Output.setdefault('news_' + str(author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
    {'title':a_title, 'source':a_author, 'author': author, 'date': author_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary2,'platform': '百度新闻'})
                if succ == False:
                    pass
        return succ, Output ## 字典形式的
    def searchBaiDuWeb(self, keywords, newsNum):
        Output = {} 
        newsPerPage = 10
        numOfPage = math.ceil(newsNum/newsPerPage)
        Countor = 0
        succ = False
        print('百度网页平台搜索关键词：' + keywords)
        for k in range (0, numOfPage):
            url = 'https://www.baidu.com/s?wd=' + keywords + '&pn=%s&cl=0&tn=baidurt&ie=utf-8&rtt=1&bsst=1'% (k* newsPerPage)
            headers = {'User-Agent': utils.get_random_user_agent()}
            response = myResponse(url=url,headers=headers)
            soup = BeautifulSoup(response.text,'html.parser')
            div_items = soup.find_all('td', class_ = 'f') 
            if len(div_items) < newsPerPage:
                numOfPage = k + 1
            
            for div in div_items:
                if Countor >= int(newsNum):
                    break
                Countor = Countor + 1
                # 去除title,连接
                try:
                    a_title = div.find('h3', class_='t').find('a').get_text().replace(u'\xa0',u' ').replace('\t','').replace('\n','') #获得 h3标签下，class为c-title的内容，然后在其中，获得a标签下的所有文本内容
                except Exception as e:
                    a_title = '标题解析错误'
                try:
                    a_href = div.find('h3', class_='t').find('a').get('href') # 获得链接
                except Exception as e:
                    a_href = '链接解析错误'
                try:
                    a_summary = div.find('font', size='-1').get_text().replace(u'\xa0',u' ').replace('\t','').replace('\n','')     # 获得简介
                except Exception as e:
                    a_summary = '简介解析错误'
                try:
                    a_author = div.find('div', class_='realtime').get_text().replace(u'\xa0',u' ').replace('\t','').replace('\n','')
                    a_summary2 = a_summary[len(a_author): len(a_summary)].replace(div.find('font', size='-1').find('font').get_text().replace(u'\xa0',u' ').replace('\t','').replace('\n',''),'')
                except Exception as e:
                    a_author = '作者解析错误 日期解析错误 时间解析错误'
                # 拆分a_author
                source = str(a_author)
                source = source.split(' ')
                source = filter(lambda x: x != '',source) # 去除空元素
                source = [i for i in source]
                
                time_flag = False  # True： 准确时间， False，大约时间，需要在后续时间进行更新
                if len(source) == 3:
                    now = int(datetime.datetime.now().timestamp())
                    author = source[0]
                    delta_time_str = source[2]
                    if '分钟' in delta_time_str:
                        delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                        author_time_format = time.localtime(now - delta_time)
                        author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)               
                    elif '小时' in delta_time_str:
                        delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                        author_time_format = time.localtime(now - delta_time)
                        author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)                  
                    elif '天' in delta_time_str:
                        delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600*24 # s，大约估计时间   
                        author_time_format = time.localtime(now - delta_time)
                        author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)                  
                    else:
                        '2017-09-25'
                        temp_date = delta_time_str.split('-')
                        try:
                            author_date = temp_date[0] + '年' +  temp_date[1] + '月' + temp_date[2] + '日' + ' --:--'
                            time_flag = True
                        except Exception as e:
                            author_date = '日期解析错误'
                    succ = True
                else: 
                    author = '作者解析错误'
                    author_date = '日期解析错误'
                    succ = True
                # 新建字典
                temptime = datetime.datetime.now()
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary2 + '\n')
                    continue  
                Output.setdefault('news_' + str(author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
        {'title':a_title, 'source':a_author, 'author': author, 'date': author_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary2,'platform': '百度网页'}) 
        return succ, Output ## 字典形式的    
## 搜索 搜狗新闻
    
    def searchSouGouNews(self, keywords, newsNum):

        print('搜狗新闻平台搜索关键词：' + keywords)
        if datetime.datetime.now().timestamp() < self.souGou_Thresh:
           print(str(datetime.datetime.now().timestamp()) + '--' + str(self.souGou_Thresh))
           errMsg = '搜狗新闻平台遭遇反爬虫系统，休息中！剩余时间：' +  str(math.floor((self.souGou_Thresh - datetime.datetime.now().timestamp())/60)) + ' 分钟！'  
           print(errMsg)
           return False, {}
        Output = {} 
        newsPerPage = 10
        numOfPage = math.ceil(newsNum/newsPerPage)
        Countor = 0
        succ = False
        for k in range (0, numOfPage):
            time.sleep(1)
            url = 'http://news.sogou.com/news?query='+ keywords + '&page=%s&p=76330300&dp=1'% (k + 1)
            headers = {'User-Agent': utils.get_random_user_agent()}

            request_Try = 0
            maxTry = 50
            request_Succ = False
            while True:
                try:
                    request_Try += 1
                    proxy = {'http':requests.get(url='http://127.0.0.1:5010/get/').text}
       #             print('#搜狗新闻# 关键词 %s 第 %s 次尝试, 使用代理：%s' % (keywords, request_Try, proxy))
                    response = requests.get(url = url, headers = headers, proxies = proxy, timeout = 4)
                    response.encoding = 'GBK'
                    soup = BeautifulSoup(response.text,'lxml')
                    if '404 Not Found' in soup.text or ('Authentication Required' in soup.text) or ('Authentication required' in soup.text) or "To protect our users, we can't process this request" in soup.text or 'HTTP/1.1 400 Bad Request' in soup.text:
      #                 print('网页抓取失败：%s' % soup.text)
                        pass
                    else:
                        pass
      #                  print('网页抓取成功！')
                        request_Succ = True     
                        break
                    if request_Try > maxTry:
                        break
                except Exception as e:
                    if request_Try > maxTry:
                        break
            
            response = myResponse(url=url, headers = headers,encode = 'GBK')
            soup = BeautifulSoup(response.text,'lxml')
            div_items = soup.find_all('div', class_ = 'vrwrap') 
            if len(div_items) == 0:
                if not request_Succ:#'找到相关新闻约0篇' not in response.text and '请检查您输入的关键词是否有错误' not in response.text and '404 Not Found' in response.text:
                    errMsg = '搜狗新闻平台遭遇反爬虫系统！'
                    print(errMsg)
  #                  print(soup.text)
                    self.write2Log(response.text)
                    sendEmail(errMsg + '\n' + response.text)
                    # WeChat.SendWeChatMsgToUserList(self.Master, errMsg, self.logfile)
#                    self.souGou_Thresh = datetime.datetime.now().timestamp() + self.souGou_RestTime*60 # 休息2小时
                else:
                    print('该页没有找到 %s 相关新闻！' % keywords)
 #                   print(soup.text)
            if len(div_items) < newsPerPage:
                numOfPage = k + 1
            for div in div_items:
                if div == div_items[-1]:
                    continue # 搜狗新闻中最后一条无效，跳过
                # 去除title,连接
                if Countor >= int(newsNum):
                    break
                try:
                    a_title = div.find('h3', class_='vrTitle').find('a').get_text() #获得 h3标签下，class为c-title的内容，然后在其中，获得a标签下的所有文本内容
                except Exception as e:
                    a_title = '标题解析错误'
                try:
                    a_href = div.find('h3', class_='vrTitle').find('a').get('href') # 获得链接
                except Exception as e:
                    a_href = '链接解析错误'
                try:
                    a_summary = div.find('div', class_='news-detail').find('p', class_='news-txt').find('span').get_text()      # 获得简介
                except Exception as e:
                    try:
                        a_summary = div.find('div', class_='news-detail').find('p', class_='news-txt').get_text().replace(u'\xa0',u' ').replace(u'\2122',u'TM')
                    except Exception as e:
                        a_summary = '简介解析错误'
                try:
                    a_author = div.find('div', class_='news-detail').find('p', class_="news-from").get_text().replace(u'\xa0',u' ').replace(u'\2122',u'TM')
                except Exception as e:
                    a_author = '作者解析错误 日期解析错误'
                # 拆分a_author
                source = str(a_author)
                source = source.split(' ')
#                print(source)
                source = filter(lambda x: x != '',source) # 去除空元素
                source = [i for i in source]
                time_flag = False  # True： 准确时间， False，大约时间，需要在后续时间进行更新
                # source所有可能类型：慧聪纺织网资讯中心 1小时前，新浪财经 2017-10-21，中国安防展览网 30分钟前，
                if len(source) == 2: 
                    now = int(datetime.datetime.now().timestamp())
                    succ = True
                    if a_author == '作者解析错误 日期解析错误':
                        author = '作者解析错误'
                        author_date = '日期解析错误'
                    else:               
                        author = source[0]
                        delta_time_str = source[1]
                        if '分钟' in author or '小时' in author:
                            # 这种情况下，一般是author不存在
                            author = '作者解析错误'
                            author_date  = source[1] + ' ' + source[2]
                            succ = True
                        else: # 作者存在
                            delta_time = 0
                            if '分钟' in delta_time_str:
                                delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                                author_time_format = time.localtime(now - delta_time)
                                author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                            elif '小时' in delta_time_str:
                                delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                                author_time_format = time.localtime(now - delta_time)
                                author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                            else:
                                temp_date = delta_time_str.split('-')
                                try:
                                    author_date = temp_date[0] + '年' +  temp_date[1] + '月' + temp_date[2] + '日' + ' --:--'
                                    time_flag = True
                                except Exception as e:
                                    author_date = '日期解析错误'
                elif len(source) ==  1:
                     # 作者不存在（时间为小时或者分钟形式）或者时间不存在（仅为作者）
                     if '分钟' in source[0] or '小时' in source[0]:
                         # 无作者
                         author = '作者解析错误'                       
                         now = int(datetime.datetime.now().timestamp())
                         # 有种情况是作者不存在
                         delta_time_str = source[0]
                         delta_time = 0
                         if '分钟' in delta_time_str:
                             delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                         else:
                             delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                         author_time_format = time.localtime(now - delta_time)
                         author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                     else: # 时间不存在
                         author = source[0]
                         author_date = '日期解析错误'
                         time_flag = True
                     succ = True
                else: 
                    author = '作者解析错误'
                    author_date = '日期解析错误'                    
                # 新建字典
                temptime = datetime.datetime.now()
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary + '\n')
                    continue
                Countor = Countor + 1
                Output.setdefault('news_' + str(author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
    {'title':a_title, 'source':a_author, 'author': author, 'date': author_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary,'platform': '搜狗新闻'}) 
 #       print(Output)
        return succ, Output ## 字典形式的
## 搜索 搜狗|微信公众平台
    
    def searchSouGou_WeChatNews(self, keywords, newsNum):
        print('搜狗-微信公众号平台搜索关键词：' + keywords)
        if datetime.datetime.now().timestamp() < self.souGou_WeChat:
           print(str(datetime.datetime.now().timestamp()) + '--' + str(self.souGou_WeChat))
           errMsg = '搜狗-微信公众号平台遭遇反爬虫系统，休息中！剩余时间：' +  str(math.floor((self.souGou_WeChat - datetime.datetime.now().timestamp())/60)) + ' 分钟！' 
           print(errMsg)
           return False, {}
        newsNum = 50 # 微信公众号强制性只搜索 50条新闻
        Output = {} 
        newsPerPage = 10
        numOfPage = math.ceil(newsNum/newsPerPage)
        Countor = 0
        succ = False
        for k in range (0, numOfPage):
            url = 'http://weixin.sogou.com/weixin?usip=&query='+ keywords + '&ft=&tsn=1&et=&interation=&type=2&wxid=&page=%s&ie=utf8'% (k + 1) # tsn = 1表示只搜索当日新闻
            headers = {'User-Agent': utils.get_random_user_agent()}
            
            request_Try = 0
            maxTry = 10
            request_Succ = False
            while True:
                try:
                    request_Try += 1
                    proxy = {'http':requests.get(url='http://127.0.0.1:5010/get/').text}
                    print('#搜狗微信# 关键词 %s 第 %s 次尝试, 使用代理：%s' % (keywords, request_Try, proxy))
                    response = requests.get(url = url, headers = headers, proxies = proxy, timeout = 4)
                    response.encoding = 'utf-8'
                    soup = BeautifulSoup(response.text,'lxml')
                    if '用户您好，您的访问过于频繁，为确认本次访问为正常用户行为' in soup.text or ('Authentication Required' in soup.text) or ('Authentication required' in soup.text) or "To protect our users, we can't process this request" in soup.text or 'HTTP/1.1 400 Bad Request' in soup.text:
                       print('网页抓取失败：%s' % soup.text)
                    else:
                        print('网页抓取成功！')
                        request_Succ = True     
                        break
                    if request_Try > maxTry:
                        break
                except Exception as e:
                    if request_Try > maxTry:
                        break            
            
            response = myResponse(url=url,headers=headers, encode = 'utf-8')
            print(response.text)
            soup = BeautifulSoup(response.text,'lxml')
            div_items = soup.find_all('div', class_ = 'txt-box') 
            if len(div_items) == 0:
                if not request_Succ:
#                and '用户您好，您的访问过于频繁，为确认本次访问为正常用户行为' in response.text:
                    errMsg = '搜狗-微信公众号平台遭遇反爬虫系统！'
                    print(errMsg)
  #                  print(soup.text)
  #                   WeChat.SendWeChatMsgToUserList(self.Master, errMsg, self.logfile)
                    self.souGou_WeChat = datetime.datetime.now().timestamp() + self.souGou_RestTime*60 # 休息2小时
                    return False, {}
                else:
                    print('搜狗-微信 该页没有找到 %s 相关新闻！' % keywords)
 #                   print(soup.text)
        #    print(div_items)
            for div in div_items:
                if Countor >= int(newsNum):
                    break
                Countor = Countor + 1                    
                # 去除title,连接
                try:
                    a_title = div.find('h3').find('a').get_text() #获得 h3标签下，class为c-title的内容，然后在其中，获得a标签下的所有文本内容
                except Exception as e:
                    a_title = '标题解析错误'
                try:
                    a_href = div.find('h3').find('a').get('href') # 获得链接
                except Exception as e:
                    a_href = '链接解析错误'
                try:
                    a_summary = div.find('p', class_='txt-info').get_text()      # 获得简介
                except Exception as e:
                    a_summary = '简介解析错误'
                try:
                    a_author = div.find('div', class_='s-p').find('a', class_="account").get_text()
                except Exception as e:
                    a_author = '作者解析错误'
                try:
                    a_date = time.localtime(int(re.findall(r'(\w*[0-9]+)\w*',div.find('div', class_='s-p').find('span').get_text())[0]))
                    a_date = '%04d年%02d月%02d日 %02d:%02d'%(a_date.tm_year, a_date.tm_mon, a_date.tm_mday, a_date.tm_hour, a_date.tm_min)
                except Exception as e:
                    a_date = '日期解析错误'            
                time_flag = True  # True： 准确时间， False，大约时间，需要在后续时间进行更新
                succ = True
                # 新建字典
                temptime = datetime.datetime.now()
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary + '\n')
                    continue                
                Output.setdefault('news_' + str(a_author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
    {'title':a_title, 'source':a_author, 'author': a_author, 'date': a_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary,'platform': '搜狗-微信公众号'}) 
#        print(Output)
            if len(div_items) < newsPerPage: # 如果页面结束，则停止搜搜
                numOfPage = k + 1
        return succ, Output ## 字典形式的

## 搜索 今日头条
    def searchJinRiTouTiao(self, keywords, newsNum):
        print('今日头条搜索关键词：' + keywords)
        Output = {} 
        newsPerReq = 10
        Countor = 0
        offset = 0
        succ = False
        time_flag = False        
        while Countor < newsNum:
            url = 'http://www.toutiao.com/search_content/?offset=' + str(offset) + '&format=json&keyword=' + keywords + '&autoload=true&count=' + str(newsPerReq) +  '&cur_tab=1'
        #    time.sleep(random.randint(3, 5))
            wbdata = requests.get(url).text
#            wbdata.encoding = 'utf-8'
            data = json.loads(wbdata)
            news = data['data']
            offset += newsPerReq
            Countor += newsPerReq
            for item in news:
                if 'title' in item.keys() and item['title']:
                    a_title = item['title']
                    Countor += 1
                else:
                    continue
                if 'source' in item.keys() and item['source']:
                    a_author = item['source']
                else:
                    a_author = '来源无法解析'
                    print(item['source'])
                if 'article_url' in item.keys() and item['article_url']:
                    a_href = item['article_url']
                else:
                    if 'url' in item.keys() and item['url']:
                        a_href = item['url']
                    else:
                        a_href = '链接无法解析'   
                        print(item['article_url'])
                if 'abstract' in item.keys() and item['abstract']:
                    a_summary = item['abstract']
                else:
                    a_summary = '简介无法解析' 
                    print(item['abstract'])             
                if 'datetime' in item.keys() and item['datetime']:
                    a_date2 = item['datetime']
                    time_flag = True
                    try:
                        a_date = time.strptime(a_date2, "%Y年%m月%d日 %H:%M:%S")
                        time_flag = True
                    except Exception as e:
                        a_date = a_date2
                else:
                    a_date = '日期无法解析'  
                    print(item['datetime'])  
                temptime = datetime.datetime.now()    
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary + '\n')
                    continue
                Output.setdefault('news_' + str(a_author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
        {'title':a_title, 'source':a_author, 'author': a_author, 'date': a_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary,'platform': '今日头条'})   
 #           print(Output)
            if len(Output) > 0:
                succ = True
            return succ, Output ## 字典形式的
    
    def writeNews2File(self, sortedNewsDic, fileName, header, mode):
        # 只在新闻有变动的时候才更新
        try:
            with open(fileName, mode, encoding='utf-8') as file:
                with self.mu:
                    file.write(header)
                    for news in sortedNewsDic:
                        body = news[1]
                        file.write("标题: " + body['title'] + "\n")
                        source = body['author'] + '  ' + body['date'] + ''
                        if not body['timeflag']:
                            source = source + '(大约)'
                        file.write("来源: " + source + "\n")
                        file.write("链接: " + body['link'] + "\n")
                        file.write("简介: " + body['summary'] + "\n\n")
        except Exception as e: # 一般错误，通知管理员即可
            errmsg = '# 新闻写入文件异常 writeNews2File:' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(errmsg))
            pass
    def sortNewsbyDate(self, newsDic):
        # 将字典按照'date'排序
        return sorted(newsDic.items(),key = lambda d:d[1]['date'], reverse = True)
    def sortNewsbyAuthor(self,newsDic):
        # 将字典按照'date'排序
        return sorted(newsDic.items(),key = lambda d:d[1]['author'], reverse = True)
    def getNews(self, keywords, numOfNews, sortMethod):
        # 返回排序后的新闻列表
        succ, news = self.scrapNews(keywords, int(numOfNews))
        sortednews = []
        if succ:
            if sortMethod == 'date':
                sortednews = self.sortNewsbyDate(news)
            elif sortMethod == 'author':
                sortednews = self.sortNewsbyAuthor(news)
            else:
                # 不排序
                with  self.mu:
                    for item in news:
                        sortednews.append((item, news[item]))
#                print('# 错误: in getNews(): 新闻排序方法未定义，按照默认date排序!\n')
#               sortednews = self.sortNewsbyDate(news)
        return succ, sortednews
    def sameNews(self, news1, news2):
        # new1 和 new2是仅包含'author', 'date', 'link', 'source', 'summary', 'timeflag', 'ttitle'的新闻字典 
        # 如果两条新闻，author 和 title一样，则认为是同一条新闻
        var_Forward = ' 【疑似转载】 '
        if news1['title'] == news2['title']:
            if news1['author'].replace(var_Forward,'') == news2['author'].replace(var_Forward,''):
                return True # 如果标题与作者均相同，则同一条新闻
            else:
                # 标题相同，作者不同，则通过判断发表时间，将后发表的标记为[疑似转载]
                try:
                    date1 = dateParser.parse(news1['date'].replace('--','').replace('年','-').replace('月','-').replace('日','')).timestamp()
                    date2 = dateParser.parse(news2['date'].replace('--','').replace('年','-').replace('月','-').replace('日','')).timestamp()
                    if date1 > date2:
                        news1['author'] = news1['author'].replace(var_Forward,'').replace('[疑似转载]','')
                        news1['author'] +=var_Forward
                    else:
                        news2['author'] = news2['author'].replace(var_Forward,'').replace('[疑似转载]','')
                        news2['author'] +=var_Forward
                    return False
                except Exception as e:
                    print('# 判断是否转载：日期格式解析错误！')
                    return True
        else:
            return False
    def updateDateStamp(self, sortedNewsDic):
        with self.mu:
            temp_sortedNewsDic = sortedNewsDic
            for k in range(len(sortedNewsDic)):  ##已有的库
                body = sortedNewsDic[k][1]
                timeStamp = body['timeflag']
                if not timeStamp:
                     findNews = False
                     updatedtimeStamp = ''
                     timeFlag = False
                     if not findNews:
                         succ, news_temp = self.scrapNews(body['title'], 60)   # 如果找不到，从最近20条中找
                         if succ:
                             for newsItem in news_temp:
                                 if self.sameNews(news_temp[newsItem], body):
                                     updatedtimeStamp = news_temp[newsItem]['date']
                                     timeFlag = news_temp[newsItem]['timeflag']
                                     findNews = True
                                     break
                     if findNews:
                         temp_sortedNewsDic[k][1]['date'] = updatedtimeStamp
                         temp_sortedNewsDic[k][1]['timeflag'] = timeFlag
                         msg = '新闻' + '## ' + temp_sortedNewsDic[k][1]['title'] + ' ## 的时间戳更新:\n 从 ' + sortedNewsDic[k][1]['date'] + ' 更新为：' + updatedtimeStamp
                         if timeFlag:
                             msg = msg + '\n 时间改为准确值！'
                         msg = msg + '\n'
                         self.write2Log(msg)
                         print(msg)
        return   temp_sortedNewsDic
