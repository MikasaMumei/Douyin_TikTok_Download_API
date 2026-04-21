import asyncio
import os
from urllib.parse import urlencode

import yaml
from pywebio.input import TEXT, actions, input, input_group, select, textarea
from pywebio.output import put_code, put_info, put_link, put_markdown, put_table, put_warning

from app.web.views.ViewsUtils import ViewsUtils
from crawlers.douyin.web.web_crawler import DouyinWebCrawler

DouyinWebCrawler = DouyinWebCrawler()

config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)


def parse_user_posts():
    form_data = input_group(
        ViewsUtils.t('解析抖音用户主页作品', 'Parse Douyin user posts'),
        [
            input(ViewsUtils.t('用户主页链接', 'User profile URL'), name='profile_url', type=TEXT,
                  required=True,
                  placeholder='https://www.douyin.com/user/xxx'),
            input(ViewsUtils.t('标题关键词', 'Title keyword'), name='keyword', type=TEXT,
                  placeholder=ViewsUtils.t('可留空', 'Optional')),
            input(ViewsUtils.t('标签(逗号分隔)', 'Tags (comma separated)'), name='tags', type=TEXT,
                  placeholder='#旅行,#美食'),
            input(ViewsUtils.t('标题正则', 'Title regex'), name='title_regex', type=TEXT,
                  placeholder=ViewsUtils.t('可留空', 'Optional')),
            input(ViewsUtils.t('最低点赞数', 'Minimum likes'), name='min_digg', type=TEXT, value='0'),
            input(ViewsUtils.t('每页抓取数', 'Page size'), name='page_size', type=TEXT, value='50'),
            input(ViewsUtils.t('最大抓取页数', 'Max pages'), name='max_pages', type=TEXT, value='20'),
            input(ViewsUtils.t('最大作品数', 'Max items'), name='max_items', type=TEXT, value='200'),
            select(ViewsUtils.t('作品类型', 'Content type'), name='aweme_type',
                   options=[
                       {'label': ViewsUtils.t('全部', 'All'), 'value': 'all'},
                       {'label': ViewsUtils.t('视频', 'Video'), 'value': 'video'},
                       {'label': ViewsUtils.t('图集', 'Image'), 'value': 'image'},
                   ], value='all'),
            select(ViewsUtils.t('标签匹配方式', 'Tag matching mode'), name='match_mode',
                   options=[
                       {'label': ViewsUtils.t('命中任意标签', 'Match any tag'), 'value': 'any'},
                       {'label': ViewsUtils.t('必须命中全部标签', 'Match all tags'), 'value': 'all'},
                   ], value='any'),
            actions(name='action', buttons=[
                {'label': ViewsUtils.t('预览结果', 'Preview results'), 'value': 'preview'},
                {'label': ViewsUtils.t('生成批量下载链接', 'Generate batch download link'), 'value': 'download'},
            ])
        ]
    )

    params = {
        'profile_url': form_data['profile_url'],
        'keyword': form_data['keyword'],
        'tags': form_data['tags'],
        'title_regex': form_data['title_regex'],
        'min_digg': int(form_data['min_digg'] or 0),
        'page_size': min(max(int(form_data['page_size'] or 50), 1), 50),
        'max_pages': int(form_data['max_pages'] or 20),
        'max_items': int(form_data['max_items'] or 200),
        'aweme_type': form_data['aweme_type'],
        'match_mode': form_data['match_mode'],
    }

    put_markdown('---')
    put_info(ViewsUtils.t('正在请求抖音用户作品，请稍候...', 'Fetching Douyin user posts, please wait...'))
    batch_data = asyncio.run(
        DouyinWebCrawler.get_user_post_videos_batch_by_profile_url(
            profile_url=params['profile_url'],
            max_pages=params['max_pages'],
            page_size=params['page_size'],
            max_items=params['max_items'],
        )
    )
    filtered_items = DouyinWebCrawler.filter_user_post_videos(
        aweme_list=batch_data.get('aweme_list', []),
        keyword=params['keyword'],
        tags=[tag.strip() for tag in params['tags'].split(',') if tag.strip()],
        title_regex=params['title_regex'],
        min_digg=params['min_digg'],
        aweme_type=params['aweme_type'],
        match_mode=params['match_mode'],
    )

    put_markdown(ViewsUtils.t('## 解析结果', '## Parsing results'))
    put_table([
        [ViewsUtils.t('字段', 'Field'), ViewsUtils.t('值', 'Value')],
        [ViewsUtils.t('sec_user_id', 'sec_user_id'), batch_data.get('sec_user_id', '')],
        [ViewsUtils.t('抓取总数', 'Fetched total'), batch_data.get('total', 0)],
        [ViewsUtils.t('过滤后数量', 'Filtered total'), len(filtered_items)],
        [ViewsUtils.t('原始返回总数', 'Raw fetched total'), batch_data.get('raw_total', batch_data.get('total', 0))],
        [ViewsUtils.t('分页页数', 'Fetched pages'), batch_data.get('fetched_pages', 0)],
        [ViewsUtils.t('作品类型过滤', 'Content type filter'), params['aweme_type']],
    ])

    if batch_data.get('warning'):
        put_warning(
            ViewsUtils.t(
                f"检测到抖音分页异常：{batch_data.get('warning_detail') or batch_data.get('warning')}。当前结果可能并非完整主页作品列表。",
                f"Douyin pagination anomaly detected: {batch_data.get('warning_detail') or batch_data.get('warning')}. Current results may be incomplete."
            )
        )

    if not filtered_items:
        put_warning(ViewsUtils.t('没有匹配到作品，请调整筛选条件。', 'No posts matched. Please adjust filters.'))
        return

    preview_rows = [[
        ViewsUtils.t('序号', 'Index'),
        ViewsUtils.t('作品ID', 'Aweme ID'),
        ViewsUtils.t('类型', 'Type'),
        ViewsUtils.t('标题', 'Title'),
        ViewsUtils.t('标签', 'Tags'),
        ViewsUtils.t('点赞', 'Likes'),
    ]]
    for index, item in enumerate(filtered_items[:20], start=1):
        preview_rows.append([
            index,
            item.get('aweme_id', ''),
            item.get('type', ''),
            item.get('desc', ''),
            ', '.join(item.get('hashtags', [])),
            item.get('statistics', {}).get('digg_count', 0),
        ])
    put_table(preview_rows)

    api_query = urlencode({k: v for k, v in params.items() if v not in ('', None)})
    api_url = f"/api/douyin/web/fetch_user_post_videos_batch?{api_query}"
    download_url = f"/api/download/douyin_user_posts_batch?{api_query}"
    put_markdown(ViewsUtils.t('### 调用链接', '### API links'))
    put_link(ViewsUtils.t('查看批量查询 API 结果', 'View batch query API result'), api_url, new_window=True)
    put_markdown('')
    put_link(ViewsUtils.t('下载批量 ZIP 文件', 'Download batch ZIP file'), download_url, new_window=True)

    if form_data['action'] == 'download':
        put_markdown(ViewsUtils.t('### 批量下载链接', '### Batch download link'))
        put_code(download_url)
