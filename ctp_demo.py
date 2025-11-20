#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: ctp_swig_build
@FileName   : ctp_demo.py
@Date       : 2025/9/15 16:13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 编译出的md和td模块导入测试
"""
import ctp.thostmduserapi as mdapi
import ctp.thosttraderapi as tdapi


def main():
    print("欢迎使用CTP接口封装工具")
    version_md = mdapi.CThostFtdcMdApi.GetApiVersion()
    print("行情接口获取当前版本号为：", version_md)

    version_td = tdapi.CThostFtdcTraderApi.GetApiVersion()
    print("交易接口获取当前版本号为：", version_td)


if __name__ == "__main__":
    main()
