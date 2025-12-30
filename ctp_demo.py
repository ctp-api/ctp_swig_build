#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @ProjectName: ctp_demo
# @FileName   : ctp_demo.py
# @Time       : 2025/3/2 19:20
# @Author     : Donny
# @Email      : donnymoving@gmail.com
# @Software   : PyCharm
# 描述：CTP行情API示例
import traceback
from pathlib import Path
from typing import Any

import ctp_api.thostmduserapi as mdapi


class CFtdcMdSpi(mdapi.CThostFtdcMdSpi):

    def __init__(self, md_user_api, setting: dict[str, Any]):
        mdapi.CThostFtdcMdSpi.__init__(self)
        self.md_user_api = md_user_api
        self.broker_id = setting["broker_id"]
        self.investor_id = setting["investor_id"]
        self.password = setting["password"]

        self.req_id: int = 0  # 请求ID
        self.login_status: bool = False  # 登录状态
        self.connect_status: bool = False  # 连接状态
        # 订阅一些常用的期货合约（SimNow模拟环境中的活跃合约）
        self.subscribe_symbol_list = ["SA601", "FG601"]

    def OnFrontConnected(self):
        """
        服务器连接成功回报
        :return:
        """
        print("CTP行情API回调 OnFrontConnected - 行情服务器连接成功")
        login_field = mdapi.CThostFtdcReqUserLoginField()
        login_field.BrokerID = self.broker_id
        login_field.UserID = self.investor_id
        login_field.Password = self.password
        print("开始登录......")
        ret = self.md_user_api.ReqUserLogin(login_field, 0)
        if ret == 0:
            print("发送登录请求成功")
        else:
            print("发送登录请求失败")

    def OnRspUserLogin(self, *args):
        """
        用户登录请求回报
        :param args:
        :return:
        """
        print("CTP行情API回调 OnRspUserLogin")
        rsp_login_field = args[0]
        rsp_info_field = args[1]
        print("SessionID=", rsp_login_field.SessionID)
        print("ErrorID=", rsp_info_field.ErrorID)
        print("ErrorMsg=", rsp_info_field.ErrorMsg)
        if rsp_info_field.ErrorID == 0:
            print("行情服务器登录成功")
            self.login_status = True

            # 获取需要重新订阅的合约列表
            symbol_bytes_list = [s.encode('utf-8') for s in self.subscribe_symbol_list]
            print(f"symbol_bytes_list={symbol_bytes_list}")

            ret = self.md_user_api.SubscribeMarketData(symbol_bytes_list, len(symbol_bytes_list))
            if ret == 0:
                print("发送订阅行情请求成功")
            else:
                print("发送订阅行情请求失败")
        else:
            self.login_status = False
            print(f"行情服务器登录失败: {rsp_info_field.ErrorMsg}")

    def OnRtnDepthMarketData(self, pDepthMarketData):
        """接收深度行情推送"""
        print("CTP行情API回调: OnRtnDepthMarketData")
        print(f"收到行情: 合约={pDepthMarketData.InstrumentID}, 最新价={pDepthMarketData.LastPrice}")

    def OnRspSubMarketData(self, *args):
        """接收订阅行情应答"""
        print("CTP行情API回调: OnRspSubMarketData")
        field = args[0]
        rsp_info = args[1]

        if rsp_info and rsp_info.ErrorID != 0:
            print('订阅行情失败！\n'
                  '订阅代码：{}\n'
                  '错误信息为：{}\n'
                  '错误代码为：{}'.format(field.InstrumentID, rsp_info.ErrorMsg, rsp_info.ErrorID))
        else:
            print('订阅{}行情成功！'.format(field.InstrumentID))


class MarketData(object):
    def __init__(self, setting: dict[str, Any]):
        self.md_api = None
        self.md_setting = setting

    @staticmethod
    def _prepare_address(address: str) -> str:
        """
        如果没有方案，则帮助程序会在前面添加 tcp:// 作为前缀。
        :param address:
        :return:
        """
        if not any(address.startswith(scheme) for scheme in ["tcp://", "ssl://", "socks://"]):
            return "tcp://" + address
        return address

    def create_md_api(self) -> None:
        """
        连接服务器
        :return:
        """
        address = self._prepare_address(self.md_setting["md_address"])

        ctp_con_dir: Path = Path.cwd().joinpath("con")

        if not ctp_con_dir.exists():
            ctp_con_dir.mkdir()

        api_path_str = str(ctp_con_dir) + "\\md"
        print("CtpMdApi：尝试创建路径为 {} 的 API".format(api_path_str))
        ctp_version = mdapi.CThostFtdcMdApi.GetApiVersion()
        print("CTP版本", ctp_version)
        try:
            # 加上utf-8编码，否则中文路径会乱码
            self.md_api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi(api_path_str.encode("GBK").decode("utf-8"))
            md_spi = CFtdcMdSpi(self.md_api, self.md_setting)
            self.md_api.RegisterSpi(md_spi)
            self.md_api.RegisterFront(address)
            print("尝试使用地址初始化 API：{}...".format(address))
            self.md_api.Init()
            print("init 调用成功")
            # join的目的是为了阻塞主线程
            self.md_api.Join()
        except Exception as e_init:
            print("初始化失败！错误：{}".format(e_init))
            print("初始化回溯：{}".format(traceback.format_exc()))
            return


if __name__ == '__main__':
    # CTP配置（使用SimNow测试环境）
    ctp_setting = {
        "investor_id": "160219",      # 输入你的simnow用户名
        "password": "Donny$1991",         # 输入你的simnow密码
        "broker_id": "9999",    # 经纪商代码
        "md_address": "tcp://182.254.243.31:30011",     # 行情服务器地址
        # "md_address": "tcp://182.254.243.31:40011",   # 7x24 行情服务器地址
        "appid": "simnow_client_test",
        "auth_code": "0000000000000000"
    }

    market = MarketData(ctp_setting)
    market.create_md_api()
