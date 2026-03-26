import streamlit as st
import os
import shutil
from pathlib import Path
import datetime
import numpy as np
import re

# ================= 配置 =================
DATA_FILE_NAME = "f107_ap.npz"
# =======================================

st.set_page_config(page_title="NRLMSIS Final Fix", page_icon="🏆")
st.title("🏆 NRLMSIS-2.0 最终修正版")

# 1. 准备数据文件
current_dir = Path(__file__).parent.resolve()
source_path = current_dir / DATA_FILE_NAME

if not source_path.exists():
    st.error(f"❌ 找不到 {DATA_FILE_NAME}")
    st.stop()

st.success(f"✅ 找到数据文件：{source_path}")

# 2. 加载数据到内存
try:
    _LOCAL_DATA = np.load(str(source_path), allow_pickle=True)
    # 确保数据是 numpy 数组
    _LOCAL_DATES = _LOCAL_DATA['dates']
    _LOCAL_F107 = _LOCAL_DATA['f107']
    _LOCAL_AP = _LOCAL_DATA['ap']
    st.success("✅ 空间天气数据已加载到内存")
except Exception as e:
    st.error(f"加载数据失败: {e}")
    st.stop()

# 3. 【核心大招】Monkey Patch: 强制离线并修正返回值格式
def _offline_get_f107_ap(dates):
    """
    完全离线的替代品。
    返回格式必须符合 pymsis 最新版本的期望：一个包含 dates, f107, ap 的字典。
    """
    dates = np.asarray(dates, dtype=np.datetime64)
    
    # 找到每个请求日期在本地数据中的最近索引
    # 避免广播错误，确保形状匹配
    if dates.ndim == 0:
        dates = np.array([dates])
        
    indices = np.argmin(np.abs(_LOCAL_DATES[:, None] - dates[None, :]), axis=0)
    
    retrieved_f107 = _LOCAL_F107[indices]
    retrieved_ap = _LOCAL_AP[indices]
    
    # 【关键】返回字典格式，而不是元组！
    return {
        "dates": dates,          # 返回请求的日期
        "f107": retrieved_f107,  # 返回对应的 F10.7
        "ap": retrieved_ap       # 返回对应的 Ap
    }

# 执行替换
import pymsis.utils
import pymsis.msis

# 1. 替换获取数据的函数
pymsis.utils.get_f107_ap = _offline_get_f107_ap

# 2. 替换加载函数，防止它尝试加载空数据或联网
# 我们让它返回 None，这样 get_f107_ap 就会被强制调用
pymsis.utils._load_f107_ap_data = lambda: None
pymsis.utils._DATA = None # 清空全局缓存

# 3. 替换下载函数，防止意外调用
pymsis.utils.download_f107_ap = lambda: None

st.info("🛡️ 安全模式已激活：拦截网络请求并修正数据格式。")

# 4. 运行计算
st.divider()
st.subheader("🚀 开始智能计算")

time_val = datetime.datetime(2023, 1, 1, 12, 0, 0)
lon_val = 0.0
lat_val = 45.0
alt_val = 400.0

base_option = {
    'f107': 150.0, 
    'f107a': 150.0, 
    'ap': 4.0, 
    'ap_prev': 4.0
}

def run_msis_with_auto_retry(t, l, la, a, base_opt):
    from pymsis import msis
    
    current_options = [base_opt]
    
    try:
        # 第一次尝试
        output = msis.run([t], [l], [la], [a], options=current_options)
        return output, 1
    except ValueError as e:
        error_msg = str(e)
        if "needs to be a list of length" in error_msg:
            match = re.search(r"length (\d+)", error_msg)
            if match:
                needed_len = int(match.group(1))
                st.write(f"⚙️ 检测到输入被广播为 {needed_len} 个点，正在自动适配...")
                
                current_options = [base_opt] * needed_len
                
                # 重试
                output = msis.run([t], [l], [la], [a], options=current_options)
                return output, needed_len
        raise e

with st.spinner("正在计算大气参数..."):
    try:
        output, final_len = run_msis_with_auto_retry(time_val, lon_val, lat_val, alt_val, base_option)
        
        st.success(f"✅ 计算成功！(内部处理了 {final_len} 个数据点)")
        
        # 解析结果
        if output.ndim == 2:
            first_point = output[0]
        else:
            reshaped = output.reshape(-1, 11)
            first_point = reshaped[0]
            
        temp = float(first_point[0])
        density = float(first_point[1])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="中性温度 (Temperature)", value=f"{temp:.2f} K")
        with col2:
            st.metric(label="总质量密度 (Density)", value=f"{density:.2e} kg/m³")
            
        st.balloons()
        st.success("🏆 完美！NRLMSIS-2.0 已在 Streamlit Cloud 上完全离线运行！")
        
        with st.expander("查看完整输出数据"):
            st.write(f"输出形状: {output.shape}")
            st.dataframe(output.reshape(-1, 11)[:5])

    except Exception as e:
        st.error(f"💥 发生未预期的错误: {e}")
        import traceback
        st.code(traceback.format_exc())
