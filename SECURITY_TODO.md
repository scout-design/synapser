# 安全待办清单 (Security TODO)

> 项目安全增强建议，按优先级排序

## ✅ 已完成

- [x] 内容安全检查 - 恶意代码、敏感词、可疑URL
- [x] 请求频率限制 (Rate Limit)
- [x] 日志脱敏
- [x] 每日发布限量 (防洪水)

## 🔴 高优先级

- [ ] **强制 HTTPS** - 配置 SSL 证书
- [ ] **Token 过期机制** - 添加 token 有效期
- [ ] **CORS 限制** - 限制允许的域名
- [ ] **登录失败限制** - 密码/OTP 错误次数限制

## 🟡 中优先级

- [ ] **API Key 权限分级** - 读取/写入/管理权限
- [ ] **跨租户访问检查** - 确保只能操作自己的数据
- [ ] **数据库敏感字段加密** - 加密存储 email 等
- [ ] **SSRF 防护** - 禁止内网 IP 访问

## 🟢 低优先级

- [ ] **CSRF Token** - 防止跨站请求
- [ ] **验证码** - 防止机器人
- [ ] **订阅数量上限** - 防止恶意订阅
- [ ] **内容相似度检测** - 防止垃圾信息
- [ ] **URL 域名信誉检查** - 钓鱼链接过滤

## 📝 配置建议

部署时建议配置：

```bash
# 必填
ENABLE_CONTENT_CHECK=true
RATE_LIMIT_ENABLED=true
DAILY_LIMIT=50

# 建议
HTTPS_ENABLED=true
CORS_ALLOWED_ORIGINS=https://yourdomain.com
TOKEN_EXPIRE_HOURS=720  # 30天
```

---

> 建议每季度审查一次安全清单，及时更新
