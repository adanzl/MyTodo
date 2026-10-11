"""`core.auth_policy` 的单元测试。

这些接口的鉴权策略此前没有任何测试覆盖，而它的失效方式是**静默**的：
`_is_whitelisted` 一旦把 `/pic/delete` 判成白名单，删除接口就会在无凭证的情况下
放行，没有任何报错。所以这里把「必须鉴权」和「必须免鉴权」两侧都锁住。
"""

from core.auth_policy import ALWAYS_AUTH_PATHS, always_requires_auth, normalize_path


class TestNormalizePath:
    def test_strips_api_prefix(self):
        """WSGI 挂在 /api 下时 request.path 不带前缀，但两种形态都要能识别。"""
        assert normalize_path('/api/pic/delete') == '/pic/delete'
        assert normalize_path('/pic/delete') == '/pic/delete'

    def test_strips_trailing_slash(self):
        assert normalize_path('/pic/delete/') == '/pic/delete'
        assert normalize_path('/api/pic/delete/') == '/pic/delete'

    def test_handles_root_and_empty(self):
        assert normalize_path('') == '/'
        assert normalize_path('/') == '/'
        assert normalize_path('/api') == '/'
        assert normalize_path('/api/') == '/'

    def test_does_not_strip_unrelated_prefix(self):
        """只有 /api 是挂载前缀，/apixyz 不能被误切。"""
        assert normalize_path('/apixyz/pic/delete') == '/apixyz/pic/delete'
        assert normalize_path('/pic/delete') == '/pic/delete'


class TestAlwaysRequiresAuth:
    def test_delete_requires_auth_in_both_path_forms(self):
        for path in ('/pic/delete', '/api/pic/delete', '/pic/delete/', '/api/pic/delete/'):
            assert always_requires_auth(path) is True, path

    def test_get_all_keeps_its_existing_carve_out(self):
        assert always_requires_auth('/getAll') is True
        assert always_requires_auth('/api/getAll') is True

    def test_upload_requires_auth_in_both_path_forms(self):
        """上传会写磁盘，未鉴权时任何人都能上传（可能被用来塞满磁盘）。"""
        for path in ('/pic/upload', '/api/pic/upload', '/pic/upload/', '/api/pic/upload/'):
            assert always_requires_auth(path) is True, path

    def test_view_must_stay_anonymous(self):
        """`<img src>` 不会带 Authorization 头，view 一旦要求鉴权图片就全裂。"""
        assert always_requires_auth('/pic/view') is False
        assert always_requires_auth('/api/pic/view') is False

    def test_other_pic_endpoints_are_not_forced(self):
        # 任何新增的 pic 写接口都应显式评估后再决定是否加入 ALWAYS_AUTH_PATHS
        assert always_requires_auth('/pic/rename') is False

    def test_unrelated_paths_are_not_forced(self):
        assert always_requires_auth('/chat/messages') is False
        assert always_requires_auth('/pic/deletex') is False
        assert always_requires_auth('/pic/uploadx') is False
        assert always_requires_auth('/xpic/delete') is False

    def test_policy_contents_are_explicit(self):
        """内容显式列出，避免有人无意间放宽。"""
        assert ALWAYS_AUTH_PATHS == frozenset({'/getAll', '/pic/delete', '/pic/upload'})
