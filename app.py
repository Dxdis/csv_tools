import streamlit as st
import pandas as pd

# 设置网页的标题和布局
st.set_page_config(page_title="一站式 CSV 处理工具", layout="wide")

st.title("🧰 一站式 CSV 合并与校对工具")

# === 聪明的读取函数，解决编码报错问题 ===
def smart_read_csv(uploaded_file):
    """尝试用不同编码读取 CSV 文件，防止 UnicodeDecodeError"""
    try:
        # 首先尝试默认的 utf-8 编码
        return pd.read_csv(uploaded_file, encoding='utf-8')
    except UnicodeDecodeError:
        # 如果报错了，就把文件指针拨回开头，换成 gbk 编码再读一次
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding='gbk')

# 使用选项卡将功能分开（增加到了 3 个选项卡）
tab1, tab2, tab3 = st.tabs(["📁 批量合并", "🔍 两表校对", "🗂️ 批量按条件提取"])

# ==========================================
# 选项卡 1：CSV 合并功能
# ==========================================
with tab1:
    st.header("批量合并 CSV 文件")
    st.write("你可以拖拽多个文件到下方，合并后可以重命名并下载。")
    
    uploaded_files = st.file_uploader("拖拽多个 CSV 文件到这里", type="csv", accept_multiple_files=True, key="merge_uploader")
    
    if uploaded_files:
        if st.button("开始合并", type="primary"):
            dfs = []
            for file in uploaded_files:
                df = smart_read_csv(file)
                dfs.append(df)
            
            merged_df = pd.concat(dfs, ignore_index=True)
            st.success(f"✅ 成功合并了 {len(uploaded_files)} 个文件，总计产生 {len(merged_df)} 行数据！")
            
            st.write("合并结果预览（前 10 行）：")
            st.dataframe(merged_df.head(10))
            
            st.divider()
            new_file_name = st.text_input("为合并后的文件命名（需包含 .csv 后缀）：", value="merged_result.csv")
            
            csv_data = merged_df.to_csv(index=False).encode('utf-8-sig') 
            st.download_button(
                label="📥 下载合并后的表格",
                data=csv_data,
                file_name=new_file_name,
                mime="text/csv",
            )

# ==========================================
# 选项卡 2：CSV 校对与比对功能
# ==========================================
with tab2:
    st.header("校对两批数据文件")
    
    col1, col2 = st.columns(2)
    with col1:
        file_a = st.file_uploader("上传 表格 A (基准表)", type="csv", key="file_a")
    with col2:
        file_b = st.file_uploader("上传 表格 B (比对表)", type="csv", key="file_b")
        
    if file_a and file_b:
        df_a = smart_read_csv(file_a)
        df_b = smart_read_csv(file_b)
        
        st.subheader("⚙️ 设置校对规则")
        
        col3, col4 = st.columns(2)
        with col3:
            key_a = st.selectbox("选择【表格 A】中用于比对的列：", df_a.columns)
        with col4:
            key_b = st.selectbox("选择【表格 B】中用于比对的列：", df_b.columns)
            
        compare_mode = st.radio(
            "你想查看什么结果？", 
            ["找出两表共有的【重复项】", "找出【表格 A】独有的【差异项】", "找出【表格 B】独有的【差异项】"]
        )
        
        if st.button("开始自动校对", type="primary", key="compare_btn"):
            df_a[key_a] = df_a[key_a].astype(str).str.strip()
            df_b[key_b] = df_b[key_b].astype(str).str.strip()
            
            if compare_mode == "找出两表共有的【重复项】":
                result_df = df_a[df_a[key_a].isin(df_b[key_b])]
                st.info(f"🔍 查验完成：找到 {len(result_df)} 条共有的重复数据。")
            elif compare_mode == "找出【表格 A】独有的【差异项】":
                result_df = df_a[~df_a[key_a].isin(df_b[key_b])]
                st.info(f"🔍 查验完成：表格 A 中有 {len(result_df)} 条数据缺失于表格 B。")
            else:
                result_df = df_b[~df_b[key_b].isin(df_a[key_a])]
                st.info(f"🔍 查验完成：表格 B 中有 {len(result_df)} 条数据缺失于表格 A。")
                
            st.dataframe(result_df)
            
            if not result_df.empty:
                csv_result = result_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下载当前校对结果",
                    data=csv_result,
                    file_name="compare_result.csv",
                    mime="text/csv",
                )

# ==========================================
# 选项卡 3：批量按条件提取功能 (新增)
# ==========================================
with tab3:
    st.header("批量按条件提取数据")
    st.write("上传一批结构相同的 CSV 文件，选择某一列并输入特定内容，程序将为你提取所有符合条件的行并合并。")
    
    extract_files = st.file_uploader("拖拽多个 CSV 文件到这里", type="csv", accept_multiple_files=True, key="extract_uploader")
    
    if extract_files:
        # 先读取第一个文件，为了获取这批文件的共有“表头”
        first_file_df = smart_read_csv(extract_files[0])
        columns = first_file_df.columns.tolist()
        
        # 读取完表头后，把第一个文件的读取指针拨回开头，以免一会儿正式提取时漏掉它
        extract_files[0].seek(0)
        
        st.subheader("⚙️ 设置提取条件")
        col5, col6 = st.columns(2)
        with col5:
            filter_col = st.selectbox("请选择要筛选的列：", columns, key="filter_col")
        with col6:
            filter_value = st.text_input(f"请输入【{filter_col}】中要提取的具体内容：", placeholder="例如：0129_done.csv")
            
        if st.button("开始批量提取", type="primary", key="extract_btn"):
            if not filter_value:
                st.warning("⚠️ 请先输入要提取的具体内容！")
            else:
                extracted_dfs = []
                total_rows = 0
                
                # 遍历所有上传的文件
                for file in extract_files:
                    df = smart_read_csv(file)
                    # 确保当前文件确实有这一列
                    if filter_col in df.columns:
                        # 【防坑机制】同样强制转为字符串并去两端空格，确保精确匹配
                        df[filter_col] = df[filter_col].astype(str).str.strip()
                        target_value = str(filter_value).strip()
                        
                        # 核心提取逻辑
                        matched_df = df[df[filter_col] == target_value]
                        
                        if not matched_df.empty:
                            extracted_dfs.append(matched_df)
                            total_rows += len(matched_df)
                            
                if extracted_dfs:
                    # 将所有提取到的结果合并
                    final_extract_df = pd.concat(extracted_dfs, ignore_index=True)
                    st.success(f"✅ 提取完成！共从 {len(extract_files)} 个文件中提取到了 {total_rows} 行符合条件的数据。")
                    st.dataframe(final_extract_df)
                    
                    # 动态生成下载文件的名称，比如: 提取结果_0129_done.csv
                    safe_filename = str(filter_value).replace('/', '_').replace('\\', '_')
                    csv_extract = final_extract_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 下载提取结果",
                        data=csv_extract,
                        file_name=f"提取结果_{safe_filename}.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("🤷‍♂️ 在所有上传的文件中，都没有找到匹配该内容的数据。请检查输入是否准确（注意大小写和空格）。")