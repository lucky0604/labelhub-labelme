# -*- coding: utf-8 -*-
"""
@Time    : 3/19/21 5:55 PM
@Author  : Lucky
@Email   : lucky_soft@163.com
@File    : dateutil.py
@Desc    : Description about this file
"""
import datetime
import json

class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self,obj)
