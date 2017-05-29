#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Weikai Wang"

import asyncio, logging
import aiomysql


# 打印SQL查询语句
def log(sql, args=()):
    logging.info("SQL: %s" % sql)


# 创建一个全局的连接池，每个HTTP请求都从池中获得数据库连接
async def create_pool(loop, **kw):
    logging.info("create database connection pool...")
    # 全局变量__pool用于存储整个连接池
    global __pool
    __pool = await aiomysql.create_pool(
        # **kw参数可以包含所有连接需要用到的关键字参数
        # 默认本机IP
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        # 默认最大连接数为10
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        # 接收一个event_loop实例
        loop=loop
    )


# 封装SQL SELECT语句为select函数
async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 执行SQL语句
            # SQL语句的占位符为?，MySQL的占位符为%s
            await cur.execute(sql.replace('?', '%s'), args or ())
            # 根据指定返回的size，返回查询的结果
            if size:
                rs = await cur.fetchmany(size)
            else:
                # 返回所有查询结果
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs

# 封装INSERT, UPDATE, DELETE
# 语句操作参数一样，所以定义一个通用的执行函数
# 返回操作影响的行号
async def execute(sql, args, autocommit=True):
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise

        return affected


# 根据输入的参数生成占位符列表
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    # 以','为分隔符，将列表合成字符串
    return ', '.join(L)


# 定义Field类，负责保存(数据库)表的字段名和字段类型
class Field(object):
    # 表的字段包含名字、类型、是否为表的主键和默认值
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    # 当打印(数据库)表时，输出(数据库)表的信息:类名，字段类型和名字
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 定义不同类型的衍生Field
# 表的不同列的字段的类型不一样
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)
