"""
简单API下载模块
提供非交互式的下载接口，所有参数通过kwargs传入
不依赖ColorfulConsole，使用内置的DummyConsole替代
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Union, List

from src.application.TikTokDownloader import TikTokDownloader
from src.application.main_terminal import TikTok
from src.config import Parameter, Settings
from src.manager import Database, DownloadRecorder
from src.module import Cookie
from src.record import BaseLogger, LoggerManager
from src.custom import PROJECT_ROOT

import requests

# 定义支持的操作类型
SUPPORTED_ACTIONS = [
    'detail', 'account', 'comment', 'search', 'info', 
    'live', 'mix', 'hashtag', 'slides', 'user', 'hot'
]

# 定义支持的文件格式
SUPPORTED_FORMATS = ['csv', 'xlsx', 'sql', 'text']

# 定义支持的账号标签
ACCOUNT_TABS = ['post', 'favorite', 'collection']

# 定义支持的搜索类型
SEARCH_TYPES = ['general', 'user', 'video', 'live']


class DummyConsole:
    """模拟控制台的简单类，用于API模式，避免依赖ColorfulConsole"""
    
    def __init__(self, debug=False):
        self.debug_mode = debug
    
    def info(self, message, log=True, **kwargs):
        """信息输出"""
        if self.debug_mode:
            print(f"[INFO] {message}")
    
    def warning(self, message, **kwargs):
        """警告输出"""
        if self.debug_mode:
            print(f"[WARNING] {message}")
    
    def error(self, message, **kwargs):
        """错误输出"""
        if self.debug_mode:
            print(f"[ERROR] {message}")
    
    def print(self, message, style=None, **kwargs):
        """普通输出"""
        if self.debug_mode:
            print(message)
    
    def input(self, prompt="", style=None, **kwargs):
        """输入提示（API模式下返回空字符串）"""
        return ""
    
    def success(self, message, **kwargs):
        """成功输出"""
        if self.debug_mode:
            print(f"[SUCCESS] {message}")
    
    def debug_log(self, message, **kwargs):
        """调试输出"""
        if self.debug_mode:
            print(f"[DEBUG] {message}")
    
    def debug(self, *args, highlight=False, **kwargs):
        """调试输出（兼容ColorfulConsole接口）"""
        if self.debug_mode:
            print(f"[DEBUG] {' '.join(str(arg) for arg in args)}")


async def API_download(cookie: str, action: str, **kwargs) -> dict:
    """
    非交互式下载API函数
    
    参数:
        cookie (str): 必需的cookie字符串
        action (str): 必需的操作类型，支持以下选项:
            - "detail": 下载作品(抖音/TikTok)
            - "account": 下载账号作品(抖音/TikTok) 
            - "live": 获取直播推流地址(抖音/TikTok)
            - "comment": 采集作品评论数据(抖音)
            - "mix": 下载合集作品(抖音/TikTok)
            - "user": 采集账号详细数据(抖音)
            - "search": 采集搜索结果数据(抖音)
            - "hot": 采集抖音热榜数据(抖音)
            - "collection": 下载收藏作品(抖音)
            - "collection_music": 下载收藏音乐(抖音)
            - "collects": 下载收藏夹作品(抖音)
            - "detail_unofficial": 下载视频原画(TikTok)
        **kwargs: 可变参数，支持以下参数:
            - urls (str|list): 要下载的链接或链接列表
            - tiktok (bool): 是否为TikTok平台，默认False(抖音)
            - download_path (str): 下载路径，默认使用项目根目录
            - cookie_tiktok (str): TikTok平台的cookie
            - proxy (str): 代理设置
            - proxy_tiktok (str): TikTok代理设置
            - max_retry (int): 最大重试次数，默认5
            - chunk (int): 下载块大小，默认131072
            - timeout (int): 超时时间，默认10
            - storage_format (str): 存储格式，可选csv,xlsx,sqlite等
            - download (bool): 是否下载文件，默认True
            - dynamic_cover (bool): 是否下载动态封面，默认False
            - static_cover (bool): 是否下载静态封面，默认False
            - music (bool): 是否下载音乐，默认False
            - folder_mode (bool): 是否使用文件夹模式，默认False
            - account_tab (str): 账号作品类型，可选"post","favorite","collection"等
            - search_keyword (str): 搜索关键词(用于search action)
            - search_type (str): 搜索类型，可选"general","user","video","live"
            - max_pages (int): 批量下载账号喜欢作品、收藏作品或者采集作品评论数据时，请求数据的最大次数（不包括异常重试），默认99999（不限制）
    
    返回:
        dict: 包含操作结果信息的字典
    """
    
    # 获取参数
    urls = kwargs.get('urls', '')
    tiktok_platform = kwargs.get('tiktok', False)
    # 设置默认下载路径为downloads目录
    downloads_dir = str(Path(PROJECT_ROOT) / "downloads")
    download_path = kwargs.get('download_path', downloads_dir)
    cookie_tiktok = kwargs.get('cookie_tiktok', '')
    proxy = kwargs.get('proxy', None)
    proxy_tiktok = kwargs.get('proxy_tiktok', None)
    max_retry = kwargs.get('max_retry', 5)
    chunk = kwargs.get('chunk', 131072)
    timeout = kwargs.get('timeout', 10)
    storage_format = kwargs.get('storage_format', '')
    download_files = kwargs.get('download', True)
    dynamic_cover = kwargs.get('dynamic_cover', False)
    static_cover = kwargs.get('static_cover', False)
    music = kwargs.get('music', False)
    folder_mode = kwargs.get('folder_mode', False)
    account_tab = kwargs.get('account_tab', 'post')
    search_keyword = kwargs.get('search_keyword', '')
    search_type = kwargs.get('search_type', 'general')
    max_pages = kwargs.get('max_pages', 1)
    
    # 验证action参数
    valid_actions = [
        "detail", "account", "live", "comment", "mix", "user", 
        "search", "hot", "collection", "collection_music", 
        "collects", "detail_unofficial"
    ]
    
    if action not in valid_actions:
        return {
            'success': False,
            'message': f'无效的action参数: {action}。支持的操作: {", ".join(valid_actions)}',
            'downloaded_count': 0,
            'failed_count': 0,
            'details': []
        }
    
    result = {
        'success': False,
        'message': '',
        'downloaded_count': 0,
        'failed_count': 0,
        'details': []
    }
    
    try:
        # 根据action类型验证必需参数
        if action in ["detail", "detail_unofficial", "account", "live", "comment", "mix", "user"] and not kwargs.get('urls'):
            result['message'] = f'{action}操作需要提供urls参数'
            return result
        elif action == "search" and not search_keyword.strip():
            result['message'] = 'search操作需要提供search_keyword参数'
            return result
        
        # 确保urls是列表格式（对于需要urls的操作）
        urls = kwargs.get('urls', '')
        if action in ["detail", "detail_unofficial", "account", "live", "comment", "mix", "user", "collects"]:
            if isinstance(urls, str):
                if not urls.strip():
                    result['message'] = '未提供有效的链接'
                    return result
                urls = [urls]
            elif isinstance(urls, list):
                if not urls or not any(url.strip() for url in urls if isinstance(url, str)):
                    result['message'] = '未提供有效的链接'
                    return result
            else:
                result['message'] = 'urls参数格式错误，必须是字符串或字符串列表'
                return result
        
        # 创建控制台对象
        console = DummyConsole(debug=False)
        
        # 创建设置对象
        settings = Settings(PROJECT_ROOT, console)
        
        # 创建Cookie对象并设置Cookie
        cookie_obj = Cookie(settings, console)
        
        # 创建数据库对象
        database = Database()
        
        async with database:
            # 读取默认配置
            config_data = await database.read_config_data()
            option_data = await database.read_option_data()
            
            config = {i["NAME"]: i["VALUE"] for i in config_data}
            option = {i["NAME"]: i["VALUE"] for i in option_data}
            
            # 创建下载记录器
            recorder = DownloadRecorder(database, config.get("Record", 1), console)
            
            # 设置日志记录器
            logger_class = LoggerManager if config.get("Logger", 0) else BaseLogger
            
            # 创建参数对象
            parameter = Parameter(
                settings=settings,
                cookie_object=cookie_obj,
                logger=logger_class,
                console=console,
                cookie=cookie,
                cookie_tiktok=cookie_tiktok,
                root=download_path,
                accounts_urls=[],
                accounts_urls_tiktok=[],
                mix_urls=[],
                mix_urls_tiktok=[],
                folder_name="Download",
                name_format="create_time type nickname desc",
                desc_length=64,
                name_length=128,
                date_format="%Y-%m-%d %H:%M:%S",
                split="-",
                music=music,
                folder_mode=folder_mode,
                truncate=50,
                storage_format=storage_format,
                dynamic_cover=dynamic_cover,
                static_cover=static_cover,
                proxy=proxy,
                proxy_tiktok=proxy_tiktok,
                twc_tiktok="",
                download=download_files,
                max_size=0,
                chunk=chunk,
                max_retry=max_retry,
                max_pages=max_pages,
                run_command="",
                owner_url={},
                owner_url_tiktok={},
                live_qualities="",
                ffmpeg="",
                recorder=recorder,
                browser_info={},
                browser_info_tiktok={},
                timeout=timeout,
                douyin_platform=not tiktok_platform,
                tiktok_platform=tiktok_platform,
            )
            
            # 设置Cookie
            parameter.set_headers_cookie()
            
            # 创建TikTok下载器对象
            tiktok_downloader = TikTok(parameter, database, server_mode=True)
            
            # 根据action类型执行不同的操作
            if action in ["detail", "detail_unofficial"]:
                await _handle_detail_action(tiktok_downloader, action, urls, tiktok_platform, result)
                
            elif action == "account":
                await _handle_account_action(tiktok_downloader, urls, tiktok_platform, account_tab, result)
                
            elif action == "live":
                await _handle_live_action(tiktok_downloader, urls, tiktok_platform, result)
                
            elif action == "comment":
                if tiktok_platform:
                    result['message'] = 'TikTok平台暂不支持评论采集功能'
                    return result
                await _handle_comment_action(tiktok_downloader, urls, max_pages, result)
                
            elif action == "mix":
                await _handle_mix_action(tiktok_downloader, urls, tiktok_platform, result)
                
            elif action == "user":
                if tiktok_platform:
                    result['message'] = 'TikTok平台暂不支持用户信息采集功能'
                    return result
                await _handle_user_action(tiktok_downloader, urls, result)
                
            elif action == "search":
                if tiktok_platform:
                    result['message'] = 'TikTok平台暂不支持搜索功能'
                    return result
                await _handle_search_action(tiktok_downloader, search_keyword, search_type, result)
                
            elif action == "hot":
                if tiktok_platform:
                    result['message'] = 'TikTok平台暂不支持热榜功能'
                    return result
                await _handle_hot_action(tiktok_downloader, result)
                
            elif action in ["collection", "collection_music", "collects"]:
                if tiktok_platform:
                    result['message'] = 'TikTok平台暂不支持收藏功能'
                    return result
                await _handle_collection_action(tiktok_downloader, action, urls, result)
                    
        # 关闭客户端连接
        if parameter:
            await parameter.close_client()
            
    except Exception as e:
        result['message'] = f'初始化过程中出现错误: {str(e)}'
    
    return result


def download_sync(cookie: str, action: str, **kwargs) -> dict:
    """
    同步版本的下载函数，内部调用异步版本
    
    参数同API_download
    """
    return asyncio.run(API_download(cookie, action, **kwargs))


# 辅助处理函数
async def _handle_detail_action(tiktok_downloader, action, urls, tiktok_platform, result):
    """处理作品下载操作"""
    # 选择链接提取器
    link_extractor = tiktok_downloader.links_tiktok if tiktok_platform else tiktok_downloader.links
    
    # 处理所有链接
    all_ids = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
            
        try:
            ids = await link_extractor.run(url)
            if ids:
                all_ids.extend(ids)
                result['details'].append({
                    'url': url,
                    'extracted_ids': ids,
                    'status': 'success'
                })
            else:
                result['details'].append({
                    'url': url,
                    'extracted_ids': [],
                    'status': 'failed',
                    'error': '无法提取作品ID'
                })
                result['failed_count'] += 1
        except Exception as e:
            result['details'].append({
                'url': url,
                'extracted_ids': [],
                'status': 'failed',
                'error': str(e)
            })
            result['failed_count'] += 1
    
    if not all_ids:
        result['message'] = '没有成功提取到任何作品ID'
        return
    
    # 创建记录对象
    root, params, logger_manager = tiktok_downloader.record.run(tiktok_downloader.parameter)
    async with logger_manager(root, console=tiktok_downloader.console, **params) as record:
        try:
            if action == "detail_unofficial":
                await tiktok_downloader.handle_detail_unofficial(all_ids)
            else:
                await tiktok_downloader._handle_detail(all_ids, tiktok_platform, record)
            
            result['success'] = True
            result['downloaded_count'] = len(all_ids)
            result['message'] = f'成功处理 {len(all_ids)} 个作品'
            
        except Exception as e:
            result['message'] = f'下载过程中出现错误: {str(e)}'
            result['failed_count'] += len(all_ids)


async def _handle_account_action(tiktok_downloader, urls, tiktok_platform, account_tab, result):
    """处理账号作品下载操作"""
    link_extractor = tiktok_downloader.links_tiktok if tiktok_platform else tiktok_downloader.links
    
    try:
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            # 提取账号信息
            if tiktok_platform:
                user_ids = await link_extractor.user(url)
            else:
                user_ids = link_extractor.user(url)
            
            if not user_ids:
                result['details'].append({
                    'url': url,
                    'status': 'failed',
                    'error': '无法提取账号信息'
                })
                result['failed_count'] += 1
                continue
            
            # 创建记录对象
            root, params, logger_manager = tiktok_downloader.record.run(tiktok_downloader.parameter)
            async with logger_manager(root, console=tiktok_downloader.console, **params) as record:
                if tiktok_platform:
                    # TikTok账号处理
                    account_data = await tiktok_downloader.deal_account_works_tiktok(
                        user_ids[0], "", account_tab, record
                    )
                else:
                    # 抖音账号处理  
                    account_data = await tiktok_downloader.deal_account_works(
                        user_ids[0], "", account_tab, record
                    )
                
                if account_data:
                    result['details'].append({
                        'url': url,
                        'status': 'success',
                        'user_id': user_ids[0]
                    })
                    result['downloaded_count'] += len(account_data) if isinstance(account_data, list) else 1
                else:
                    result['details'].append({
                        'url': url,
                        'status': 'failed',
                        'error': '获取账号作品失败'
                    })
                    result['failed_count'] += 1
        
        result['success'] = True
        result['message'] = f'账号作品处理完成'
        
    except Exception as e:
        result['message'] = f'处理账号作品时出现错误: {str(e)}'


async def _handle_live_action(tiktok_downloader, urls, tiktok_platform, result):
    """处理直播推流地址获取"""
    link_extractor = tiktok_downloader.links_tiktok if tiktok_platform else tiktok_downloader.links
    
    try:
        all_live_data = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            ids = await link_extractor.run(url, type_="live")
            if not ids:
                result['details'].append({
                    'url': url,
                    'status': 'failed',
                    'error': '无法提取直播ID'
                })
                result['failed_count'] += 1
                continue
            
            # 获取直播数据
            if tiktok_platform:
                live_data = [await tiktok_downloader.get_live_data_tiktok(i) for i in ids]
            else:
                live_data = [await tiktok_downloader.get_live_data(i) for i in ids]
            
            live_data = await tiktok_downloader.extractor.run(live_data, None, "live")
            
            if live_data and any(live_data):
                all_live_data.extend([i for i in live_data if i])
                result['details'].append({
                    'url': url,
                    'status': 'success',
                    'live_count': len([i for i in live_data if i])
                })
            else:
                result['details'].append({
                    'url': url,
                    'status': 'failed',
                    'error': '获取直播数据失败'
                })
                result['failed_count'] += 1
        
        if all_live_data:
            # 处理直播下载
            if tiktok_platform:
                download_tasks = tiktok_downloader.show_live_info_tiktok(all_live_data)
            else:
                download_tasks = tiktok_downloader.show_live_info(all_live_data)
            
            await tiktok_downloader.downloader.run(download_tasks, type_="live")
            
            result['success'] = True
            result['downloaded_count'] = len(all_live_data)
            result['message'] = f'成功处理 {len(all_live_data)} 个直播'
        else:
            result['message'] = '没有获取到有效的直播数据'
            
    except Exception as e:
        result['message'] = f'处理直播时出现错误: {str(e)}'


async def _handle_comment_action(tiktok_downloader, urls, max_pages, result):
    """处理评论采集操作"""
    try:
        all_ids = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            ids = await tiktok_downloader.links.run(url)
            if ids:
                all_ids.extend(ids)
        
        if not all_ids:
            result['message'] = '没有提取到有效的作品ID'
            return
        
        # 使用comment_handle方法处理评论采集
        await tiktok_downloader.comment_handle(
            all_ids,
            tiktok=False,  # 抖音平台
            pages=max_pages,  # 传递max_pages参数
        )
        
        result['success'] = True
        result['downloaded_count'] = len(all_ids)
        result['message'] = f'成功采集 {len(all_ids)} 个作品的评论数据'
                
    except Exception as e:
        result['message'] = f'采集评论时出现错误: {str(e)}'


async def _handle_mix_action(tiktok_downloader, urls, tiktok_platform, result):
    """处理合集作品下载"""
    if isinstance(urls, str):
        urls = [urls] if urls.strip() else []
    elif not isinstance(urls, list):
        result['message'] = 'urls参数格式错误，必须是字符串或字符串列表'
        return
    
    if not urls:
        result['message'] = '未提供有效的合集链接'
        return
    
    link_extractor = tiktok_downloader.links_tiktok if tiktok_platform else tiktok_downloader.links
    
    try:
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            # 提取合集信息
            tiktok_flag, mix_ids = link_extractor.mix(url)
            
            if not mix_ids:
                result['details'].append({
                    'url': url,
                    'status': 'failed', 
                    'error': '无法提取合集ID'
                })
                result['failed_count'] += 1
                continue
            
            # 创建记录对象
            root, params, logger_manager = tiktok_downloader.record.run(tiktok_downloader.parameter)
            async with logger_manager(root, console=tiktok_downloader.console, **params) as record:
                if tiktok_platform:
                    mix_data = await tiktok_downloader.mix_batch_tiktok(mix_ids, record)
                else:
                    mix_data = await tiktok_downloader.mix_batch(mix_ids, record)
                
                if mix_data:
                    result['details'].append({
                        'url': url,
                        'status': 'success',
                        'mix_ids': mix_ids
                    })
                    result['downloaded_count'] += len(mix_data) if isinstance(mix_data, list) else 1
                else:
                    result['details'].append({
                        'url': url,
                        'status': 'failed',
                        'error': '获取合集作品失败'
                    })
                    result['failed_count'] += 1
        
        result['success'] = True
        result['message'] = '合集作品处理完成'
        
    except Exception as e:
        result['message'] = f'处理合集时出现错误: {str(e)}'


async def _handle_user_action(tiktok_downloader, urls, result):
    """处理用户信息采集"""
    if isinstance(urls, str):
        urls = [urls] if urls.strip() else []
    elif not isinstance(urls, list):
        result['message'] = 'urls参数格式错误，必须是字符串或字符串列表'
        return
    
    if not urls:
        result['message'] = '未提供有效的用户链接'
        return
    
    try:
        all_user_ids = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            user_ids = tiktok_downloader.links.user(url)
            if user_ids:
                all_user_ids.extend(user_ids)
        
        if not all_user_ids:
            result['message'] = '没有提取到有效的用户ID'
            return
        
        # 创建记录对象
        root, params, logger_manager = tiktok_downloader.record.run(tiktok_downloader.parameter)
        async with logger_manager(root, console=tiktok_downloader.console, **params) as record:
            user_data = await tiktok_downloader.account_detail_batch(all_user_ids, record)
            
            if user_data:
                result['success'] = True
                result['downloaded_count'] = len(all_user_ids)
                result['message'] = f'成功采集 {len(all_user_ids)} 个用户的详细数据'
            else:
                result['message'] = '用户数据采集失败'
                
    except Exception as e:
        result['message'] = f'采集用户数据时出现错误: {str(e)}'


async def _handle_search_action(tiktok_downloader, search_keyword, search_type, result):
    """处理搜索操作"""
    if not search_keyword.strip():
        result['message'] = '未提供搜索关键词'
        return
    
    try:
        # 创建记录对象
        root, params, logger_manager = tiktok_downloader.record.run(tiktok_downloader.parameter)
        async with logger_manager(root, console=tiktok_downloader.console, **params) as record:
            if search_type == "user":
                search_data = await tiktok_downloader.user_search_batch(search_keyword, record)
            elif search_type == "video":
                search_data = await tiktok_downloader.video_search_batch(search_keyword, record)
            elif search_type == "live":
                search_data = await tiktok_downloader.live_search_batch(search_keyword, record)
            else:  # general
                search_data = await tiktok_downloader.general_search_batch(search_keyword, record)
            
            if search_data:
                result['success'] = True
                result['downloaded_count'] = len(search_data) if isinstance(search_data, list) else 1
                result['message'] = f'成功采集关键词 "{search_keyword}" 的搜索结果'
            else:
                result['message'] = '搜索结果采集失败'
                
    except Exception as e:
        result['message'] = f'搜索时出现错误: {str(e)}'


async def _handle_hot_action(tiktok_downloader, result):
    """处理热榜数据采集"""
    try:
        # 创建记录对象
        root, params, logger_manager = tiktok_downloader.record.run(tiktok_downloader.parameter)
        async with logger_manager(root, console=tiktok_downloader.console, **params) as record:
            hot_data = await tiktok_downloader.hot_batch(record)
            
            if hot_data:
                result['success'] = True
                result['downloaded_count'] = len(hot_data) if isinstance(hot_data, list) else 1
                result['message'] = '成功采集热榜数据'
            else:
                result['message'] = '热榜数据采集失败'
                
    except Exception as e:
        result['message'] = f'采集热榜数据时出现错误: {str(e)}'


async def _handle_collection_action(tiktok_downloader, action, urls, result):
    """处理收藏相关操作"""
    try:
        # 创建记录对象
        root, params, logger_manager = tiktok_downloader.record.run(tiktok_downloader.parameter)
        async with logger_manager(root, console=tiktok_downloader.console, **params) as record:
            if action == "collection":
                collection_data = await tiktok_downloader.collection_batch(record)
            elif action == "collection_music":
                collection_data = await tiktok_downloader.collection_music_batch(record)
            elif action == "collects":
                if isinstance(urls, str):
                    urls = [urls] if urls.strip() else []
                elif not isinstance(urls, list):
                    result['message'] = 'urls参数格式错误，必须是字符串或字符串列表'
                    return
                
                if not urls:
                    result['message'] = '未提供有效的收藏夹链接'
                    return
                    
                collect_ids = []
                for url in urls:
                    url = url.strip()
                    if url:
                        ids = tiktok_downloader.links.collects(url)
                        if ids:
                            collect_ids.extend(ids)
                
                if not collect_ids:
                    result['message'] = '没有提取到有效的收藏夹ID'
                    return
                    
                collection_data = await tiktok_downloader.collects_batch(collect_ids, record)
            
            if collection_data:
                result['success'] = True
                result['downloaded_count'] = len(collection_data) if isinstance(collection_data, list) else 1
                result['message'] = f'成功处理{action}数据'
            else:
                result['message'] = f'{action}数据处理失败'
                
    except Exception as e:
        result['message'] = f'处理{action}时出现错误: {str(e)}'


def send_markdown_message(content):
    key = "c6b2ff61-ec4d-49bc-a41b-80fa935f7112"
    headers = {'Content-Type': 'application/json'}
    params = {'key': key}
    data = {"msgtype": "markdown", "markdown": {"content": content}}
    response = requests.post('https://qyapi.weixin.qq.com/cgi-bin/webhook/send', params=params, headers=headers, data=json.dumps(data))
    return response


def read_csv_first_rows(csv_path: str, rows: int = 5) -> str:
    """读取CSV文件的前几行并格式化为Markdown表格"""
    try:
        import csv
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            data = []
            for i, row in enumerate(reader):
                if i >= rows:
                    break
                data.append(row)
        
        if not data:
            return "CSV文件为空"
        
        # 格式化为Markdown表格
        if len(data) == 1:
            return f"CSV只有标题行: {', '.join(data[0])}"
        
        markdown = "CSV文件前5行:\n\n"
        
        # 表头
        if data:
            markdown += "| " + " | ".join(data[0]) + " |\n"
            markdown += "|" + "---|" * len(data[0]) + "\n"
        
        # 数据行
        for row in data[1:]:
            # 确保行的列数与表头一致
            while len(row) < len(data[0]):
                row.append("")
            markdown += "| " + " | ".join(row[:len(data[0])]) + " |\n"
        
        return markdown
        
    except Exception as e:
        return f"读取CSV文件失败: {e}"


def parse_kwargs(kwargs_str: str) -> dict:
    """解析JSON格式的kwargs参数"""
    try:
        if not kwargs_str or kwargs_str.strip() == '{}':
            return {}
        return json.loads(kwargs_str)
    except json.JSONDecodeError as e:
        print(f"❌ kwargs JSON 格式错误: {e}")
        sys.exit(1)


async def main():
    """主函数 - 处理命令行参数"""
    if len(sys.argv) < 3:
        print("用法: python api_download.py <cookie> <action> [kwargs_json]")
        print("示例: python api_download.py 'your_cookie' 'comment' '{\"urls\": \"https://...\", \"storage_format\": \"csv\"}'")
        sys.exit(1)
    
    cookie = sys.argv[1]
    action = sys.argv[2]
    kwargs_str = sys.argv[3] if len(sys.argv) > 3 else '{}'
    
    # 验证必需参数
    if not cookie:
        print("❌ 错误: Cookie参数不能为空")
        sys.exit(1)
    
    if not action:
        print("❌ 错误: Action参数不能为空")
        sys.exit(1)
    
    # 解析kwargs参数
    kwargs = parse_kwargs(kwargs_str)
    
    # 构建API调用参数
    api_params = {
        'cookie': cookie,
        'action': action,
        'tiktok': kwargs.get('tiktok', False),
    }
    
    # 添加可选参数
    for key, value in kwargs.items():
        if key not in ['cookie', 'action']:
            api_params[key] = value
    
    try:
        print(f"开始执行 {action} 操作...")
        print(f"参数: {json.dumps({k: v for k, v in api_params.items() if k != 'cookie'}, ensure_ascii=False)}")
        
        # 执行API调用
        result = await API_download(**api_params)
        
        # 输出结果
        print("\n执行结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 如果是CSV格式且操作成功，读取CSV文件前5行并发送给bot
        if (result.get('success', False) and 
            kwargs.get('storage_format') == 'csv' and 
            action in ['comment', 'search', 'account', 'detail']):
            
            # 查找生成的CSV文件
            import os
            from pathlib import Path
            import glob
            import time
            
            print("\n🔍 搜索CSV文件...")
            print(f"当前工作目录: {os.getcwd()}")
            
            # 等待一小段时间确保文件写入完成
            time.sleep(1)
            
            # 根据实际文件位置，直接搜索 Volume/downloads/Data/ 目录
            search_patterns = [
                Path("./Volume/downloads/Data") / "*.csv",
                Path("./downloads/Data") / "*.csv", 
                Path("./downloads/Download") / "*.csv",
                Path("./downloads") / "*.csv",
                Path("./") / "*.csv",
            ]
            
            csv_file = None
            
            for pattern in search_patterns:
                try:
                    files = glob.glob(str(pattern))
                    if files:
                        print(f"  ✅ 在 {pattern} 找到 {len(files)} 个文件: {files}")
                        # 选择最新的文件
                        csv_file = max(files, key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0)
                        print(f"  🎯 选择最新文件: {csv_file}")
                        print(f"  📅 文件修改时间: {time.ctime(os.path.getmtime(csv_file))}")
                        break
                    else:
                        print(f"  ❌ 在 {pattern} 未找到文件")
                except Exception as e:
                    print(f"  ⚠️ 搜索 {pattern} 时出错: {e}")
            
            # 尝试读取文件
            if csv_file and os.path.exists(csv_file):
                print(f"\n📄 找到CSV文件: {csv_file}")
                print(f"📊 文件信息:")
                stat = os.stat(csv_file)
                print(f"   - 文件大小: {stat.st_size} bytes")
                print(f"   - 修改时间: {time.ctime(stat.st_mtime)}")
                print(f"   - 绝对路径: {os.path.abspath(csv_file)}")
                
                try:
                    print("\n� 开始读取CSV内容...")
                    csv_content = read_csv_first_rows(csv_file)
                    print(f"📝 读取的CSV内容长度: {len(csv_content)} 字符")
                    print(f"📝 CSV内容预览: {csv_content[:200]}..." if len(csv_content) > 200 else f"📝 CSV内容: {csv_content}")
                    
                    print("\n🤖 调用send_markdown_message函数...")

                    response = send_markdown_message(csv_content)
                    print("✅ send_markdown_message 函数调用完成,响应:", response.text)
                    
                except Exception as e:
                    print(f"❌ 读取或发送CSV文件失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("\n❌ 未找到CSV文件")
                print("� 调试信息:")
                print(f"   - 当前目录: {os.getcwd()}")
                print(f"   - Volume目录存在: {os.path.exists('Volume')}")
                if os.path.exists('Volume'):
                    print(f"   - Volume目录内容: {os.listdir('Volume')}")
                    if os.path.exists('Volume/downloads'):
                        print(f"   - Volume/downloads目录内容: {os.listdir('Volume/downloads')}")
                        if os.path.exists('Volume/downloads/Data'):
                            print(f"   - Volume/downloads/Data目录内容: {os.listdir('Volume/downloads/Data')}")
                print(f"   - downloads目录存在: {os.path.exists('downloads')}")
                if os.path.exists('downloads'):
                    print(f"   - downloads目录内容: {os.listdir('downloads')}")
                print(f"   - 当前目录CSV文件: {[f for f in os.listdir('.') if f.endswith('.csv')]}")
        
        # 如果有错误，设置退出码
        if not result.get('success', False):
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())