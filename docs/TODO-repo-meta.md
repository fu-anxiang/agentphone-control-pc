# 待办：仓库描述与 Topics

## 状态

**未完成** —— 令牌 `coomi-use` 缺 `Administration: Read and write` 权限。

实测返回：

```
PATCH /repos/fu-anxiang/agentphone-control-pc          → 403 Resource not accessible by personal access token
PUT   /repos/fu-anxiang/agentphone-control-pc/topics   → 403 同上
```

改仓库描述 / Topics 走的是**仓库管理权限**，只给 `Contents: Read and write` 不够。

## 两个解法

### A. 给现有令牌补权限（推荐，一次设完）

1. https://github.com/settings/tokens?type=beta
2. 点 `coomi-use` → **Permissions** → 找到 **Administration** → 改成 **Read and write**
3. 保存（令牌字符串不变，无需换）
4. 然后运行：

```sh
GITHUB_TOKEN=github_pat_xxx ./bin/set-repo-meta.sh
```

### B. 网页上填两个字段（不想动令牌权限）

仓库页 → 右侧 **About** 齿轮：

- **Description**：
  ```
  用手机控制 Windows 电脑：pcrelay 边缘中继 + SSH 双通道（命令/键鼠/截屏/文件/浏览器自动化）
  ```
- **Topics**：
  ```
  windows remote-control rpc android automation ssh tailscale cloudflare-workers durable-objects powershell python
  ```

## 会设成什么

| 字段 | 值 |
|---|---|
| Description | 用手机控制 Windows 电脑：pcrelay 边缘中继 + SSH 双通道（命令/键鼠/截屏/文件/浏览器自动化） |
| Topics | windows · remote-control · rpc · android · automation · ssh · tailscale · cloudflare-workers · durable-objects · powershell · python |

## 跑完怎么确认

```sh
curl -sS https://api.github.com/repos/fu-anxiang/agentphone-control-pc \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["description"]);print(d["topics"])'
```

`bin/set-repo-meta.sh` 结尾也会自己打印一次当前状态。
