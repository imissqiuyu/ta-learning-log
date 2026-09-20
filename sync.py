# TA 学习日志 · 自动同步脚本
#
# 作用：把日志的改动提交并推送到 GitHub
#
# 运行方式：
#   · 手动：双击 `同步.cmd`
#   · 自动：Windows 计划任务定时调用
#
# 设计原则：
#   1. 网络不通时【不报错退出】，下次再试 —— 因为代理可能没开
#   2. 每一步都写进 sync.log，方便事后查
#   3. 没有改动就不提交（不留空提交）

import os
import subprocess
import sys
import time
from datetime import datetime

# ⚠️ Windows 控制台默认是 GBK，打不出 emoji 会直接崩。
#    计划任务里跑崩了是【静默失败】，所以这里必须兜住。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------- 配置
GIT = r"D:\Git\cmd\git.exe"
REPO = r"D:\ta-learning-log"
LOG = os.path.join(REPO, "sync.log")

# 代理：留空 = 不用代理（直连）
# 如果你用的是 Clash 系，通常是 http://127.0.0.1:7897
#
# 推送时会【先直连、失败再走代理】—— 这样代理开不开都能工作
PROXY = "http://127.0.0.1:7897"

# 日志文件本身不要提交（不然每次同步都会产生新改动 → 死循环）
GITIGNORE = """sync.log
*.tmp
__pycache__/
"""


def log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(args, check=False, use_proxy=False):
    """跑一条 git 命令，返回 (退出码, 输出)

    use_proxy=True 时临时带上代理参数（不写进 git 配置，避免污染全局）
    """
    cmd = [GIT]
    if use_proxy and PROXY:
        cmd += ["-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY]
    cmd += args
    try:
        p = subprocess.run(cmd, cwd=REPO, capture_output=True, timeout=180)
        out = (p.stdout + p.stderr).decode("utf-8", "replace").strip()
        if check and p.returncode != 0:
            log("  命令失败: git %s" % " ".join(args))
            log("  " + out.replace("\n", "\n  "))
        return p.returncode, out
    except subprocess.TimeoutExpired:
        log("  超时: git %s" % " ".join(args))
        return 124, "timeout"
    except Exception as e:
        log("  异常: %s" % e)
        return 1, str(e)


def main():
    if not os.path.isdir(REPO):
        log("找不到仓库目录: %s" % REPO)
        return 1
    if not os.path.isfile(GIT):
        log("找不到 git: %s" % GIT)
        return 1
    if not os.path.isdir(os.path.join(REPO, ".git")):
        log("%s 还不是 git 仓库，先跑一次初始化" % REPO)
        return 1

    # 保证 .gitignore 存在
    gi = os.path.join(REPO, ".gitignore")
    if not os.path.isfile(gi):
        with open(gi, "w", encoding="utf-8", newline="\n") as f:
            f.write(GITIGNORE)
        log("已创建 .gitignore")

    # ---- 1. 有没有改动 ----
    code, out = run(["status", "--porcelain"])
    if code != 0:
        log("git status 失败，放弃这次同步")
        return 1

    if not out.strip():
        log("没有改动，跳过提交")
    else:
        changed = len([l for l in out.splitlines() if l.strip()])
        log("发现 %d 个文件有改动，准备提交" % changed)

        run(["add", "-A"])

        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        code, out = run(["commit", "-m", "更新学习日志 %s" % stamp], check=True)
        if code != 0:
            log("提交失败，放弃这次同步")
            return 1
        log("已提交")

    # ---- 2. 推送 ----
    #   ⚠️ 这台机器上的代理是【时通时不通】的（实测：同一个 github.com
    #      可能连续 5 次超时，也可能连续 5 次 200）。
    #      所以要多试几轮，别一次失败就放弃。
    last_out = ""
    for attempt in range(1, 4):
        for tag, up in (("直连", False), ("走代理", True)):
            if up and not PROXY:
                continue
            code, last_out = run(["push", "-u", "origin", "main"], use_proxy=up)
            if code == 0:
                log("✅ 已推送到 GitHub（%s，第 %d 轮）" % (tag, attempt))
                return 0
        if attempt < 3:
            log("  第 %d 轮没推上去，等 5 秒再试" % attempt)
            time.sleep(5)

    # 三轮都失败：网络问题，不算致命，下次自动重试
    log("⚠️ 推送失败（改动已本地提交，下次会自动重试）")
    for line in last_out.splitlines()[:6]:
        log("    " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
