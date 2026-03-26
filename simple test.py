import streamlit as st
import os
import shutil
from pathlib import Path
import datetime
import sys

# ================= 配置 =================
DATA_FILE_NAME = "f107_ap.npz"
# =======================================

st.set_page_config(page_title="NRLMSIS Fix", page_icon="🛑")
st.title("🛑 NRLMSIS-2.0 强制离线模式")

# 1. 定义路径
current_dir = Path(__file__).parent.resolve()
source_path = current_dir / DATA_FILE_NAME
target_dir = Path.home() / ".pymsis"
target_path = target_dir / DATA_FILE_NAME

# 2. 【关键】强制检查源文件是否存在
# 如果这里失败，说明 GitHub 上没文件，程序直接终止，绝不尝试运行模型
st.write(f"🔍 正在检查源文件：{source_path}")
st.write(f"📂 当前工作目录：{os.getcwd()}")
st.write(f"📄 当前目录文件列表：{list(current_dir.iterdir())}") # 调试用：打印目录下所有文件

if not source_path.exists():
    st.error(f"❌ 致命错误：找不到 `{DATA_FILE_NAME}`！")
    st.error("原因：该文件未上传到 GitHub，或者文件名不匹配。")
    st.info("请检查 GitHub 仓库，确保 `f107_ap.npz` 与 `simple test.py` 在同一目录。")
    st.stop() # 强制停止，防止后续代码执行

st.success(f"✅ 找到源文件：{source_path} (大小: {source_path.stat().st_size} bytes)")

# 3. 执行复制操作
try:
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 总是覆盖，确保是最新的
    shutil.copy2(source_path, target_path)
    st.success(f"✅ 成功复制文件到缓存目录：{target_path}")
    
    # 再次验证目标文件
    if not target_path.exists():
        st.error("❌ 复制似乎失败了：目标文件不存在。")
        st.stop()
        
except Exception as e:
    st.error(f"❌ 复制文件时发生异常：{e}")
    st.stop()

# 4. 只有文件确认到位后，才导入和运行 pymsis
st.divider()
st.subheader("🚀 开始计算 (离线模式)")

with st.spinner("正在加载模型..."):
    try:
        # 此时导入，pymsis 应该会检测到文件存在
        from pymsis import msis
        
        # 测试参数
        time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        lon = 0.0
        lat = 45.0
        alt = 400.0

        # 执行计算
        # 如果这里还报 URLError，说明 pymsis 内部逻辑有变，或者文件损坏
        output = msis.run(time, lon, lat, alt)
        
        # 处理维度
        if output.ndim == 2:
            temp = float(output[0, 0])
            density = float(output[0, 1])
        elif output.ndim == 5:
            temp = float(output[0, 0, 0, 0, 0])
            density = float(output[0, 0, 0, 0, 1])
        else:
            st.error(f"未知维度：{output.ndim}")
            st.stop()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("温度 (K)", f"{temp:.2f}")
        with col2:
            st.metric("密度 (kg/m³)", f"{density:.2e}")
            
        st.success("🎉 成功！未发生网络请求。")

    except urllib.error.URLError as e:
        st.error(f"💥 仍然发生了网络错误：{e}")
        st.error("这说明文件复制虽然显示成功，但 pymsis 没有识别到。")
        st.info("尝试手动删除云端的缓存目录重试（需重新部署）。")
    except Exception as e:
        st.error(f"💥 其他错误：{e}")
        import traceback
        st.code(traceback.format_exc())
