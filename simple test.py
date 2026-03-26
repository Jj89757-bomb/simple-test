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

st.set_page_config(page_title="NRLMSIS Ultimate Fix", page_icon="🏆")
st.title("🏆 NRLMSIS-2.0 终极智能离线版")

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
    st.success("✅ 空间天气数据已加载到内存")
except Exception as e:
    st.error(f"加载数据失败: {e}")
    st.stop()

# 3. 【核心大招】Monkey Patch: 强制离线
def _offline_get_f107_ap(dates):
    """
    完全离线的替代品。
    从本地内存数据中通过最近邻插值获取 F10.7 和 Ap。
    """
    dates = np.asarray(dates, dtype=np.datetime64)
    local_dates = _LOCAL_DATA['dates']
    local_f107 = _LOCAL_DATA['f107']
    local_ap = _LOCAL_DATA['ap']
    
    # 找到每个请求日期在本地数据中的最近索引
    # 使用广播机制高效计算
    indices = np.argmin(np.abs(local_dates[:, None] - dates[None, :]), axis=0)
    
    return local_f107[indices], local_f107[indices], local_ap[indices]

# 执行替换
import pymsis.utils
pymsis.utils.get_f107_ap = _offline_get_f107_ap
pymsis.utils._load_f107_ap_data = lambda: {"dates": np.array([]), "f107": np.array([]), "ap": np.array([])}
pymsis.utils.download_f107_ap = lambda: None

st.info("🛡️ 安全模式已激活：所有网络请求已被拦截并重定向到本地数据。")

# 4. 运行计算
st.divider()
st.subheader("🚀 开始智能计算")

# 定义测试参数
time_val = datetime.datetime(2023, 1, 1, 12, 0, 0)
lon_val = 0.0
lat_val = 45.0
alt_val = 400.0

# 构造基础 Options 字典
base_option = {
    'f107': 150.0, 
    'f107a': 150.0, 
    'ap': 4.0, 
    'ap_prev': 4.0
}

def run_msis_with_auto_retry(t, l, la, a, base_opt):
    from pymsis import msis
    
    # 第一次尝试：假设只需要 1 个
    current_options = [base_opt]
    
    try:
        output = msis.run([t], [l], [la], [a], options=current_options)
        return output, 1
    except ValueError as e:
        error_msg = str(e)
        if "needs to be a list of length" in error_msg:
            # 提取需要的长度数字
            match = re.search(r"length (\d+)", error_msg)
            if match:
                needed_len = int(match.group(1))
                st.write(f"⚙️ 检测到输入被广播为 {needed_len} 个点，正在自动适配...")
                
                # 构造正确长度的 options 列表
                # pymsis 会将单个输入点广播到 needed_len 个，所以我们需要 needed_len 个相同的配置
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
        # 输出形状可能是 (N, 11) 或 (N, 1, 1, 1, 11) 等，其中 N 是 final_len
        # 我们只关心第一个点的结果
        
        # 展平数组以便处理，假设最后维度是变量 (11个)
        if output.ndim == 2:
            # 形状 (25, 11)
            first_point = output[0]
        else:
            # 重塑为 (N, 11)
            reshaped = output.reshape(-1, 11)
            first_point = reshaped[0]
            
        temp = float(first_point[0])       # Temperature
        density = float(first_point[1])    # Total Mass Density
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="中性温度 (Temperature)", value=f"{temp:.2f} K")
        with col2:
            st.metric(label="总质量密度 (Density)", value=f"{density:.2e} kg/m³")
            
        st.balloons()
        st.success("🏆 完美！NRLMSIS-2.0 已在 Streamlit Cloud 上完全离线运行！")
        
        with st.expander("查看完整输出数据"):
            st.write(f"输出形状: {output.shape}")
            st.write("变量顺序: [Temp, Density, N2, O2, O, Ar, He, H, N, NO, Mass]")
            st.dataframe(output.reshape(-1, 11)[:5]) # 显示前5行

    except Exception as e:
        st.error(f"💥 发生未预期的错误: {e}")
        import traceback
        st.code(traceback.format_exc())
