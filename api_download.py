"""
简单API下载模块
提供非交互式的下载接口，所有参数通过kwargs传入
不依赖ColorfulConsole，使用内置的DummyConsole替代
"""

import asyncio
from pathlib import Path
from typing import Optional, Union, List

from src.application.TikTokDownloader import TikTokDownloader
from src.application.main_terminal import TikTok
from src.config import Parameter, Settings
from src.manager import Database, DownloadRecorder
from src.module import Cookie
from src.record import BaseLogger, LoggerManager
from src.custom import PROJECT_ROOT


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
    download_path = kwargs.get('download_path', str(PROJECT_ROOT))
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


# 使用示例
if __name__ == "__main__":
    # 注意：此API模块已移除对ColorfulConsole的依赖，使用内置的DummyConsole替代
    # 示例用法
    example_cookie = "__live_version__=%221.1.3.9068%22; live_use_vvc=%22false%22; hevc_supported=true; enter_pc_once=1; UIFID_TEMP=e92777d2cb4cf0f94a981760c14554e8d3208daf0443679909dcdbe8e735b061ff1698d40c931ec6ea9ab67d8eda71feaf3c95d6228a0bc6c3e5c6aab9c9c74ef48414d129633bf4fdbb4851da84b1ee; dy_swidth=2560; fpk1=U2FsdGVkX18zJWQ9Zk4mRVczE20OmA2mmUSV+rsbla5PfwS7i4LwwCzLWnKlCQXtwYXfhuQCnlN6VwhPEk1LUg==; fpk2=2204ee63bef2f351470a66ffe1bb020e; s_v_web_id=verify_mh04nbep_XOIyjHEr_pqcl_4bkP_BdX9_o9uA0GRIzPtu; bd_ticket_guard_client_web_domain=2; passport_csrf_token=f7cc7213c59b372b6063833e65d4331a; passport_csrf_token_default=f7cc7213c59b372b6063833e65d4331a; UIFID=e92777d2cb4cf0f94a981760c14554e8d3208daf0443679909dcdbe8e735b0619e703945ac231b3db9a20216dd16e252dd2a1cdc61cfc39b8cce5eadf2c1861786cc35df2ae5455006a124e05e5f9a5e1e3b3b37422209a0147f71be46494ae838d0276ac254f7f7e1c7faee0193d994f9f06611d124dd052ac7ff4e352743f55cad001aaa5a95da5f98ef8f9b0bf4918be8f64101b0f01e2b1ecc19ae30f689; passport_mfa_token=Cjf7h8vcic1%2F8lPqFKEqH1ghg9AiE2dRh%2B%2B5zpEXqzfX5%2BgXxMJdSBlp1CgCnlETCla5Sw0qc06LGkoKPAAAAAAAAAAAAABPpGf8OmwjoLpz66P7hkx3%2FzYvwIwxPtJA%2Fdg7mVVnA7%2F3G9ohcJHAIc0U75O2Z6uJ%2FhDt%2F%2F8NGPax0WwgAiIBA%2FvhUM4%3D; d_ticket=d4c65af5a60342dbc91ceb00bc0d9451306f4; n_mh=p3i7kKksPF4ZDsLMIQdQbhidWGM6jgZ1qxLE48ZhqBw; is_staff_user=false; __security_server_data_status=1; login_time=1761624235757; is_dash_user=1; publish_badge_show_info=%220%2C0%2C0%2C1761624236208%22; DiscoverFeedExposedAd=%7B%7D; SelfTabRedDotControl=%5B%5D; download_guide=%223%2F20251028%2F0%22; my_rd=2; passport_assist_user=CkEu3UaUn_0g-lICdqWDKoIef2KDjFZ70_3pTCMJreiLccbBSujW2ymR-YEtc2PZibPmZLxzyA4cYRBCVs_5GxJ99BpKCjwAAAAAAAAAAAAAT6VwT10A1Ppivsh1XeNlhbqGa0KU56OguKwLdNEbv2vO7yh5u9zdwTHlsPdsptVcLcgQwYCADhiJr9ZUIAEiAQOIOPap; sid_guard=bc285b30c79eab095dddd56143298f56%7C1761632741%7C5183999%7CSat%2C+27-Dec-2025+06%3A25%3A40+GMT; uid_tt=7fa898db008697ca63f3cec003eec98b; uid_tt_ss=7fa898db008697ca63f3cec003eec98b; sid_tt=bc285b30c79eab095dddd56143298f56; sessionid=bc285b30c79eab095dddd56143298f56; sessionid_ss=bc285b30c79eab095dddd56143298f56; session_tlb_tag=sttt%7C17%7CvChbMMeeqwld3dVhQymPVv_________Tf170X8whSzmA6OSOLX2Pc4EljArhCOkvqGu5t9G_p6s%3D; sid_ucp_v1=1.0.0-KGEzNTBiYzQ0ZmIwNjExNjY1ZGFmZGQ1NDMxOWI2ODFkNGNiZjkzYTUKIQiguZDUkfTJBBDlw4HIBhjvMSAMMMLkxvAFOAdA9AdIBBoCbHEiIGJjMjg1YjMwYzc5ZWFiMDk1ZGRkZDU2MTQzMjk4ZjU2; ssid_ucp_v1=1.0.0-KGEzNTBiYzQ0ZmIwNjExNjY1ZGFmZGQ1NDMxOWI2ODFkNGNiZjkzYTUKIQiguZDUkfTJBBDlw4HIBhjvMSAMMMLkxvAFOAdA9AdIBBoCbHEiIGJjMjg1YjMwYzc5ZWFiMDk1ZGRkZDU2MTQzMjk4ZjU2; _bd_ticket_crypt_cookie=200da24e5c5f6f4b258d9a5875001e6a; __security_mc_1_s_sdk_sign_data_key_web_protect=57694f33-4ebe-b16e; __security_mc_1_s_sdk_cert_key=1df61f04-475b-84c4; __security_mc_1_s_sdk_crypt_sdk=05ddeee7-4680-8381; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.5%7D; __ac_nonce=069033e7700b3cf28bb07; __ac_signature=_02B4Z6wo00f01NlpXGAAAIDCDeXk5JPgpVzZSVjAAF9fba; douyin.com; device_web_cpu_core=24; device_web_memory_size=8; architecture=amd64; dy_sheight=1441; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A2560%2C%5C%22screen_height%5C%22%3A1441%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A24%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAA86KIUDDvtnlO02DMYxsZQn6Nd6qgnXkpRofvthpk6Gi1WzJvoSbQMyGFWLHAiE9i%2F1761840000000%2F0%2F1761820282936%2F0%22; strategyABtestKey=%221761820283.498%22; ttwid=1%7CSmRR2-ogJH8OCazFO9BMNnb9VZmxxI65orMrb-ayGes%7C1761820283%7C506c835339456f802ff4f6e97df8d348bd6dcb56d5a85c32de089869781d55ec; FRIEND_NUMBER_RED_POINT_INFO=%22MS4wLjABAAAA86KIUDDvtnlO02DMYxsZQn6Nd6qgnXkpRofvthpk6Gi1WzJvoSbQMyGFWLHAiE9i%2F1761840000000%2F1761820285833%2F0%2F0%22; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAA86KIUDDvtnlO02DMYxsZQn6Nd6qgnXkpRofvthpk6Gi1WzJvoSbQMyGFWLHAiE9i%2F1761840000000%2F0%2F1761820286087%2F0%22; biz_trace_id=96292dd1; sdk_source_info=7e276470716a68645a606960273f2771777060272927676c715a6d6069756077273f2771777060272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f273536333d3d3735373d34333234272927676c715a75776a716a666a69273f2763646976602778; bit_env=EUUqB4sEXS_E7fR4i8V0ekJjkfYedqiKa6RIYxw58QpmnCu_T4sVjcAHnJ2e5TUPP0Z0M4IeoDLYz9zy1TpjesiX1N3DbjPUeUiwNcLtVzL0U-Udm6KthsFA-sLP9808x_fAUXcch5txi3kcorHlK0O96xbO3ZzLipsFRSf2MQLXUU1gN7e2q0u22AjsQcsNcmD7qA_CZe4xOZGfT-MkJp3mqVT_tc7kfyF2PT1pa7WqaBqhKy7OrFBDUG3g7E1jk3HxVWzQZtSdmlB7jNprPMn-YBdSc-ntOp6wZGZZzPDs1zVwi-iHGecQTRHkaTxMXjZItGwhPdnpIGVPbdNuIqCLH6FLsqG-XNgJk97DnI9-NcuSZUZUXlrOuHrsTYI1c-My8IWe8NEzUBbM3GPWCyeQ_5UzzvQtWerMbqxOpR4rWhCYvFJMgEmpg3xDqwTC3wt2BZrrsVkZrv8mAHaNvrz4ojyS52ZMg_9WFPWuIfLTU7liYqiPLMdWx47XtWwo; gulu_source_res=eyJwX2luIjoiYmM5OWY5NGU3MmYzZDQ4ZDRiMWU2Mzc1MzQ3MzY4YTYwNzI5OTJmZWE2ZDJhMDFiZDE3ZWVmZjAzMTk3ZDk3NyJ9; passport_auth_mix_state=wyfti2cnxztbyeuzcq95rhdm1p5dg9hgbx5303hz0zml6cka; home_can_add_dy_2_desktop=%220%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCQXFxeUtTRVR6SlVFUDJuLzduSjg5OEZpV2FCSE5TM0tmQ29SbUtQRHhvZmhGMHNaNDI0R1JkaHpQcTlja2lYWU1UZzl0T2dCS2dNbXgreTBuTnR2dE09IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJBcXF5S1NFVHpKVUVQMm4vN25KODk4RmlXYUJITlMzS2ZDb1JtS1BEeG9maEYwc1o0MjRHUmRoelBxOWNraVhZTVRnOXRPZ0JLZ01teCt5MG5OdHZ0TT0iLCJ0c19zaWduIjoidHMuMi43YTUwMDNkMmRjYzg2NTVhYjM3Nzc2MTJkMWJhYWZiMjJmMWVhYzMzZjFmMWQ2YWZjMmZiNjEwMTZkZTcxMDdkYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiJTR2VWRWYxUEJRWTNCTHhwWkxmL2ZJeHV4RFVJenNPZWRjRjlZdTM0dU5RPSIsInNlY190cyI6IiNaQTlvTitFN1RReS9RbW1odDlLQkRtc3REV1NYTGNOWGxqWDFKdW8zd2xVU3RUcnJzNTY5cjFhcnlQcGoifQ%3D%3D; IsDouyinActive=true; playRecommendGuideTagCount=8; totalRecommendGuideTagCount=8; odin_tt=ffee98449725d741dbab8f8a521776917f21233f2d379b2319d56f832807ee99f43ce018027efdcd4faac5731539e64964e2555438ed9d4c6dc47105decfb99aef2330bc911340b42cb970bb3102af95"
    example_urls = [
        "https://www.douyin.com/user/self?from_tab_name=main&modal_id=7253355171290352955&showTab=favorite_collection"
    ]
    
    # 异步调用示例
    async def main():
        # # 下载作品
        # result1 = await API_download(
        #     cookie=example_cookie,
        #     action="detail",
        #     urls=example_urls,
        #     tiktok=False,  # False表示抖音，True表示TikTok
        #     download_path="./downloads",
        #     download=True,
        #     dynamic_cover=True,
        #     static_cover=True
        # )
        # print("作品下载结果:", result1)
        
        # # 下载账号作品（限制最大页数）
        # result2 = await API_download(
        #     cookie=example_cookie,
        #     action="account",
        #     urls="https://www.douyin.com/user/username",
        #     account_tab="post",  # post发布作品, favorite喜欢作品, collection收藏作品
        #     max_pages=10,  # 限制最多请求10页数据
        #     tiktok=False
        # )
        # print("账号作品下载结果:", result2)
        
        # 采集评论数据（限制最大页数）
        result3 = await API_download(
            cookie=example_cookie,
            action="comment",
            urls=example_urls,
            storage_format="csv",  # 保存为CSV格式
            max_pages=2,  # 限制最多请求5页评论数据
            tiktok=False
        )
        print("评论采集结果:", result3)
        
        # # 搜索功能
        # result4 = await API_download(
        #     cookie=example_cookie,
        #     action="search",
        #     search_keyword="美食",
        #     search_type="video",  # general, user, video, live
        #     storage_format="xlsx",
        #     tiktok=False
        # )
        # print("搜索结果:", result4)
        
        # # 获取直播推流地址
        # result5 = await API_download(
        #     cookie=example_cookie,
        #     action="live",
        #     urls="https://live.douyin.com/123456789",
        #     tiktok=False
        # )
        # print("直播结果:", result5)
    
    # 同步调用示例
    # result = download_sync(
    #     cookie=example_cookie,
    #     action="detail",
    #     urls=example_urls[0],  # 也可以传单个字符串
    #     tiktok=False
    # )
    # print(result)
    
    # 运行异步示例
    asyncio.run(main())