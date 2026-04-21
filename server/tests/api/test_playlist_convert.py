"""测试播放列表转换为MP3功能"""
import requests
import json

# 配置
BASE_URL = "http://127.0.0.1:8848"


def test_convert_playlist_to_mp3():
    """测试将播放列表转换为MP3格式"""

    # 首先获取所有播放列表
    print("1. 获取所有播放列表...")
    response = requests.get(f"{BASE_URL}/api/playlist/get")
    if response.status_code != 200:
        print(f"获取播放列表失败: {response.status_code}")
        return

    playlists = response.json()
    if not playlists or 'data' not in playlists:
        print("没有找到播放列表")
        return

    playlist_data = playlists['data']
    if not playlist_data:
        print("播放列表为空")
        return

    # 获取第一个播放列表的ID
    first_playlist_id = list(playlist_data.keys())[0]
    first_playlist = playlist_data[first_playlist_id]
    playlist_name = first_playlist.get('name', '未知')

    print(f"找到播放列表: {first_playlist_id} - {playlist_name}")

    # 统计文件数量
    file_count = 0
    pre_lists = first_playlist.get('pre_lists', [])
    if isinstance(pre_lists, list) and len(pre_lists) == 7:
        for pre_list in pre_lists:
            if isinstance(pre_list, list):
                file_count += len(pre_list)

    playlist_files = first_playlist.get('playlist', [])
    file_count += len(playlist_files)

    print(f"播放列表中共有 {file_count} 个文件")

    if file_count == 0:
        print("播放列表中没有文件，跳过转换测试")
        return

    # 询问用户是否继续
    confirm = input(f"\n确认要将播放列表 '{playlist_name}' 中的所有文件转换为MP3格式吗？(yes/no): ")
    if confirm.lower() != 'yes':
        print("已取消转换")
        return

    # 调用转换接口
    print(f"\n2. 开始转换播放列表 {first_playlist_id}...")
    response = requests.post(f"{BASE_URL}/api/playlist/convertToMp3",
                             json={"id": first_playlist_id},
                             headers={"Content-Type": "application/json"})

    if response.status_code != 200:
        print(f"转换请求失败: {response.status_code}")
        print(f"响应: {response.text}")
        return

    result = response.json()
    print(f"转换结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    if result.get('code') == 0:
        print("\n✓ 转换任务已成功启动")
        print("注意：转换在后台进行，可能需要一些时间完成")
        print("在转换期间，该播放列表将被锁定，无法修改")
    else:
        print(f"\n✗ 转换失败: {result.get('msg')}")


if __name__ == "__main__":
    try:
        test_convert_playlist_to_mp3()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
