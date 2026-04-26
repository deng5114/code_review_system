# Phase 2 Step 3: 安全升级 — AES-GCM 加密

**日期**: 2026-04-26
**状态**: 已完成
**测试**: 260 passed (20 new)
**覆盖率**: 96% (crypto module: 96%)

---

## 目标

将 API Key 存储从 Django signing (HMAC-SHA256) 升级为 AES-256-GCM 认证加密。

## 变更概览

### 新建文件

| 文件 | 用途 |
|------|------|
| `backend/apps/common/services/crypto.py` | AESEncryption 工具类 |
| `backend/apps/common/tests/test_crypto.py` | 加密模块单元测试 (20 tests) |
| `backend/apps/ai/migrations/0004_migrate_to_aes_gcm.py` | Django signing → AES-GCM 数据迁移 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/apps/ai/models.py` | API Key 加解密从 `signing.Signer` 切换为 AES-GCM，保留回退兼容 |
| `backend/requirements.txt` | 添加 `cryptography>=42.0.0` |
| `backend/.env.example` | 添加 `AES_ENCRYPTION_KEY` 说明和生成方法 |

## 实现细节

### AESEncryption 工具类 (`crypto.py`)

- 使用 `cryptography` 库的 `AESGCM` 类实现 AES-256-GCM 认证加密
- 32 字节加密密钥从 `AES_ENCRYPTION_KEY` 环境变量读取 (64 字符 hex 字符串)
- 12 字节随机 nonce (NIST SP 800-38D 推荐)
- 加密输出: base64(`nonce` || `ciphertext + tag`)
- `is_aes_encrypted()` 启发式方法用于区分 AES-GCM 密文和 Django signed 值
- `generate_key_hex()` 辅助函数生成随机密钥

### 模型层兼容策略 (`models.py`)

**加密 (setter)**:
1. 若 `AES_ENCRYPTION_KEY` 已配置 → 使用 AES-GCM
2. 否则 → 回退到 Django signing (dev 模式兼容)

**解密 (getter)**:
1. 若 AES 可用且值看起来像 AES 密文 → 尝试 AES-GCM 解密
2. AES 解密失败 → 回退 Django signing 解密
3. signing 也失败 → 返回原始值

### 数据迁移 (`0004_migrate_to_aes_gcm.py`)

**正向迁移**: Django signing → AES-GCM
1. 读取所有 AIConfig 记录
2. 用 `signer.unsign()` 解密原始值
3. 用 `aes.encrypt()` 重新加密
4. 直接更新数据库 (绕过 model.save() 避免验证问题)

**回滚迁移**: AES-GCM → Django signing
1. 检测 AES 加密的值
2. 解密后用 `signer.sign()` 重新签名

**安全措施**: 迁移仅在 `AES_ENCRYPTION_KEY` 已配置时执行，未配置时跳过并记录日志。

## 测试覆盖

### crypto.py 测试 (20 tests)

| 类别 | 测试数 | 覆盖场景 |
|------|--------|----------|
| 加解密 | 6 | roundtrip、不同密文、空字符串、Unicode、长密钥 |
| 安全性 | 1 | 篡改检测 (InvalidTag) |
| 可用性检查 | 5 | 有效/无效/短/非法hex密钥、环境变量读取 |
| 不可用异常 | 2 | 加密/解密时抛出 RuntimeError |
| 格式检测 | 4 | AES 密文/短字符串/Django签名/非法base64 |
| 密钥生成 | 3 | 64字符、唯一性、可用性 |

### 迁移验证

迁移脚本在无 AES 密钥时安全跳过，在有密钥时正确转换所有记录。

## 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 数据迁移失败 | HIGH | 回滚迁移保留 + BadSignature 跳过 + 日志记录 |
| 密钥丢失导致数据不可恢复 | HIGH | 迁移前备份 + 环境变量文档化 |
| nonce 碰撞 | LOW | 12 字节随机 nonce, 碰撞概率 < 2^-32 |

## 累计进度

| 指标 | Phase 2 Step 2 | Phase 2 Step 3 | 变化 |
|------|----------------|----------------|------|
| 后端测试 | 240 | 260 | +20 |
| 测试覆盖率 | 96% | 96% | - |
| 新文件 | ~13 | +3 | 16 |
| Python 依赖 | 11 | 12 | +1 (cryptography) |

## 下一步

Phase 2 Step 4: 实时进度 (WebSocket 推送审查进度)
