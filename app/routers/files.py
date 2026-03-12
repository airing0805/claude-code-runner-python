"""文件浏览器 API 路由

提供目录树、文件读取、文件搜索、文件信息等 API 端点。
"""

import os
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user_optional
from app.services.file_service import (
    MAX_READ_LINES,
    MAX_SEARCH_RESULTS,
    MAX_TREE_DEPTH,
    DirectoryNotFoundError,
    FileNotFoundError,
    FileService,
    FileServiceError,
    FileTooLargeError,
    PathValidationError,
    get_file_service,
)

router = APIRouter(prefix="/api/files", tags=["文件浏览器"])
logger = logging.getLogger(__name__)

# 获取工作目录
def get_working_dir() -> str:
    """获取工作目录"""
    return os.getenv("WORKING_DIR", ".")


# ============= 请求模型 =============

class GlobRequest(BaseModel):
    """Glob 搜索请求"""
    pattern: str = Field(..., description="Glob 模式，如 src/**/*.py")
    path: Optional[str] = Field(None, description="搜索目录")
    limit: int = Field(100, ge=1, le=500, description="限制结果数量")


# ============= 统一响应 =============

def success_response(data: any) -> dict:
    """成功响应"""
    return {"success": True, "data": data}


def error_response(error: str, code: str, status_code: int = 400) -> dict:
    """错误响应"""
    return {"success": False, "error": error, "code": code}


# ============= API 端点 =============

@router.get("/tree")
async def get_tree(
    path: str = Query(".", description="目录路径"),
    depth: int = Query(2, ge=1, le=MAX_TREE_DEPTH, description="递归深度"),
    include_hidden: bool = Query(False, description="是否包含隐藏文件"),
    current_user: Optional[any] = Depends(get_current_user_optional),
) -> dict:
    """
    获取目录文件树

    支持可选认证：
    - 已认证用户：可记录访问情况（未来扩展）
    - 匿名用户：正常访问

    返回指定目录的树形结构。
    """
    try:
        service = get_file_service(get_working_dir())
        result = service.get_tree(path, depth, include_hidden)
        return success_response({
            "path": result.path,
            "name": result.name,
            "type": result.type,
            "children": [
                {
                    "name": child.name,
                    "path": child.path,
                    "type": child.type,
                    "size": child.size,
                    "extension": child.extension,
                    "modified": child.modified,
                    "children": _serialize_children(child.children),
                }
                for child in result.children
            ],
            "metadata": result.metadata,
        })
    except PathValidationError as e:
        raise HTTPException(status_code=403, detail=error_response(e.message, e.code, 403))
    except DirectoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=error_response(e.message, e.code, 404))
    except FileServiceError as e:
        raise HTTPException(status_code=400, detail=error_response(e.message, e.code, 400))
    except Exception as e:
        raise HTTPException(status_code=500, detail=error_response(str(e), "INTERNAL_ERROR", 500))


@router.get("/read")
async def read_file(
    path: str = Query(..., description="文件路径"),
    start_line: int = Query(1, ge=1, description="起始行号"),
    limit: int = Query(500, ge=1, le=MAX_READ_LINES, description="读取行数"),
    current_user: Optional[any] = Depends(get_current_user_optional),
) -> dict:
    """
    读取文件内容

    支持可选认证：
    - 已认证用户：可记录访问情况（未来扩展）
    - 匿名用户：正常访问

    返回文件内容，支持分页读取。
    """
    try:
        service = get_file_service(get_working_dir())
        result = service.read_file(path, start_line, limit)
        return success_response({
            "path": result.path,
            "name": result.name,
            "size": result.size,
            "total_lines": result.total_lines,
            "content": result.content,
            "truncated": result.truncated,
            "has_more": result.has_more,
            "encoding": result.encoding,
        })
    except PathValidationError as e:
        raise HTTPException(status_code=403, detail=error_response(e.message, e.code, 403))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=error_response(e.message, e.code, 404))
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=error_response(e.message, e.code, 413))
    except FileServiceError as e:
        raise HTTPException(status_code=400, detail=error_response(e.message, e.code, 400))
    except Exception as e:
        raise HTTPException(status_code=500, detail=error_response(str(e), "INTERNAL_ERROR", 500))


@router.get("/search")
async def search_files(
    pattern: str = Query(..., description="Glob 模式"),
    path: str = Query(".", description="搜索目录"),
    limit: int = Query(100, ge=1, le=MAX_SEARCH_RESULTS, description="限制结果数量"),
    current_user: Optional[any] = Depends(get_current_user_optional),
) -> dict:
    """
    搜索文件

    支持可选认证：
    - 已认证用户：可记录搜索情况（未来扩展）
    - 匿名用户：正常搜索

    使用 Glob 模式搜索文件。
    """
    try:
        service = get_file_service(get_working_dir())
        result = service.search_files(pattern, path, limit)
        return success_response({
            "pattern": result.pattern,
            "matches": result.matches,
            "total": result.total,
            "truncated": result.truncated,
        })
    except PathValidationError as e:
        raise HTTPException(status_code=403, detail=error_response(e.message, e.code, 403))
    except FileServiceError as e:
        raise HTTPException(status_code=400, detail=error_response(e.message, e.code, 400))
    except Exception as e:
        raise HTTPException(status_code=500, detail=error_response(str(e), "INTERNAL_ERROR", 500))


@router.get("/info")
async def get_file_info(
    path: str = Query(..., description="文件路径"),
    current_user: Optional[any] = Depends(get_current_user_optional),
) -> dict:
    """
    获取文件信息

    支持可选认证：
    - 已认证用户：可记录访问情况（未来扩展）
    - 匿名用户：正常访问

    返回文件的元数据信息。
    """
    try:
        service = get_file_service(get_working_dir())
        result = service.get_file_info(path)
        return success_response({
            "path": result.path,
            "name": result.name,
            "type": result.type,
            "size": result.size,
            "size_formatted": result.size_formatted,
            "extension": result.extension,
            "mime_type": result.mime_type,
            "modified": result.modified,
            "created": result.created,
        })
    except PathValidationError as e:
        raise HTTPException(status_code=403, detail=error_response(e.message, e.code, 403))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=error_response(e.message, e.code, 404))
    except FileServiceError as e:
        raise HTTPException(status_code=400, detail=error_response(e.message, e.code, 400))
    except Exception as e:
        raise HTTPException(status_code=500, detail=error_response(str(e), "INTERNAL_ERROR", 500))


@router.post("/glob")
async def glob_files(
    request: GlobRequest,
    current_user: Optional[any] = Depends(get_current_user_optional),
) -> dict:
    """
    Glob 模式查询

    支持可选认证：
    - 已认证用户：可记录搜索情况（未来扩展）
    - 匿名用户：正常搜索

    使用 Glob 模式搜索文件（POST 版本）。
    """
    try:
        service = get_file_service(get_working_dir())
        result = service.search_files(
            request.pattern,
            request.path or ".",
            request.limit,
        )
        return success_response({
            "pattern": result.pattern,
            "matches": [m["path"] for m in result.matches],
            "count": len(result.matches),
        })
    except PathValidationError as e:
        raise HTTPException(status_code=403, detail=error_response(e.message, e.code, 403))
    except FileServiceError as e:
        raise HTTPException(status_code=400, detail=error_response(e.message, e.code, 400))
    except Exception as e:
        raise HTTPException(status_code=500, detail=error_response(str(e), "INTERNAL_ERROR", 500))


# ============= 辅助函数 =============

def _serialize_children(children: list) -> list:
    """序列化子节点"""
    result = []
    for child in children:
        item = {
            "name": child.name,
            "path": child.path,
            "type": child.type,
            "size": child.size,
            "extension": child.extension,
            "modified": child.modified,
        }
        if child.children:
            item["children"] = _serialize_children(child.children)
        result.append(item)
    return result
