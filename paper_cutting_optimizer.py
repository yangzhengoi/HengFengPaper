# paper_cutting_optimizer.py - 完整版本，包含恒丰纸业Logo
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from itertools import product
from collections import Counter
import time

# 设置页面配置
st.set_page_config(
    page_title="恒丰纸业 - 辊纸套切优化系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
def add_custom_css():
    st.markdown("""
    <style>
    .logo-container {
        text-align: center;
        margin-bottom: 20px;
    }
    .logo-img {
        max-width: 300px;
        height: auto;
    }
    .company-title {
        text-align: center;
        color: #1f77b4;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 辊纸套切优化器类
class PaperCuttingOptimizer:
    def __init__(self, master_width=5480, min_utilization=0.9):
        self.master_width = master_width
        self.min_utilization = min_utilization
        self.min_width = master_width * min_utilization
    
    def generate_patterns(self, widths, max_pieces=4):
        """生成所有可行的切割方案"""
        patterns = []
        
        for num_pieces in range(1, max_pieces + 1):
            for combo in product(widths, repeat=num_pieces):
                total_width = sum(combo)
                
                if total_width <= self.master_width and total_width >= self.min_width:
                    pattern_counter = Counter(combo)
                    pattern_desc = '+'.join(f"{count}×{width}" for width, count in pattern_counter.items())
                    
                    utilization = total_width / self.master_width
                    
                    patterns.append({
                        'description': pattern_desc,
                        'total_width': total_width,
                        'utilization': round(utilization, 4),
                        'composition': dict(pattern_counter),
                        'waste': self.master_width - total_width
                    })
        
        # 去重并按利用率降序排序
        unique_patterns = {}
        for pattern in patterns:
            key = tuple(sorted(pattern['composition'].items()))
            if key not in unique_patterns or pattern['utilization'] > unique_patterns[key]['utilization']:
                unique_patterns[key] = pattern
        
        return sorted(unique_patterns.values(), key=lambda x: x['utilization'], reverse=True)
    
    def find_optimal_combination(self, orders, patterns):
        """找到能完全消耗订单的最优组合"""
        best_combination = None
        best_utilization = 0
        
        for pattern in patterns:
            # 检查这个模式是否能完全匹配订单
            matches = True
            max_runs = float('inf')
            
            for width, count in pattern['composition'].items():
                if count > 0:
                    available = orders.get(width, 0)
                    if available < count:
                        matches = False
                        break
                    max_runs = min(max_runs, available // count)
            
            if matches and max_runs > 0:
                # 检查是否能完全消耗所有订单
                temp_orders = orders.copy()
                for width, count in pattern['composition'].items():
                    temp_orders[width] -= count * max_runs
                
                # 如果完全消耗了所有订单，这是一个完美方案
                if all(qty == 0 for qty in temp_orders.values()):
                    if pattern['utilization'] > best_utilization:
                        best_utilization = pattern['utilization']
                        best_combination = (pattern, max_runs)
        
        return best_combination
    
    def greedy_optimize(self, orders, max_iterations=1000):
        """贪心算法优化 - 确保完全消耗订单"""
        start_time = time.time()
        
        widths = list(orders.keys())
        patterns = self.generate_patterns(widths)
        patterns.sort(key=lambda x: x['utilization'], reverse=True)
        
        # 首先检查是否存在能完全消耗订单的单一组合
        perfect_combination = self.find_optimal_combination(orders, patterns)
        if perfect_combination:
            pattern, runs = perfect_combination
            production_plan = [{
                'pattern': pattern['description'],
                'runs': runs,
                'utilization': pattern['utilization'],
                'waste_per_coil': pattern['waste'],
                'composition': pattern['composition']
            }]
            
            total_coils_used = runs
            total_waste = pattern['waste'] * runs
            remaining_orders = {}
        else:
            # 使用逐步优化的方法
            remaining_orders = orders.copy()
            production_plan = []
            total_coils_used = 0
            total_waste = 0
            
            iteration = 0
            while any(remaining_orders.values()) and iteration < max_iterations:
                iteration += 1
                best_pattern = None
                best_score = -1
                best_runs = 0
                
                for pattern in patterns:
                    # 检查模式是否可行
                    feasible = True
                    max_runs = float('inf')
                    
                    for width, count in pattern['composition'].items():
                        if remaining_orders.get(width, 0) < count:
                            feasible = False
                            break
                        if count > 0:
                            max_runs = min(max_runs, remaining_orders.get(width, 0) // count)
                    
                    if feasible and max_runs > 0:
                        # 评分标准：利用率 + 对完成订单的贡献度
                        score = pattern['utilization']
                        
                        # 优先选择能更快完成订单的模式
                        completion_bonus = 0
                        for width, count in pattern['composition'].items():
                            if count > 0:
                                # 如果这个模式能完全消耗某个规格的剩余订单
                                if remaining_orders[width] == count * max_runs:
                                    completion_bonus += 0.2
                        
                        score += completion_bonus
                        
                        if score > best_score:
                            best_score = score
                            best_pattern = pattern
                            best_runs = max_runs
                
                if best_pattern is None:
                    # 如果没有找到可行模式，尝试放宽条件
                    for pattern in patterns:
                        max_runs = float('inf')
                        feasible = True
                        
                        for width, count in pattern['composition'].items():
                            if count > 0:
                                available = remaining_orders.get(width, 0)
                                if available < count:
                                    # 这个规格不足，但我们可以减少运行次数
                                    feasible = True
                                    max_runs = 0
                                    break
                                max_runs = min(max_runs, available // count)
                        
                        if feasible and max_runs > 0:
                            score = pattern['utilization']
                            if score > best_score:
                                best_score = score
                                best_pattern = pattern
                                best_runs = max_runs
                    
                    if best_pattern is None:
                        # 如果仍然没有找到，使用单一切割模式完成剩余订单
                        for width, quantity in remaining_orders.items():
                            if quantity > 0 and width <= self.master_width:
                                # 创建单一切割模式
                                single_pattern = {
                                    'description': f"1×{width}",
                                    'total_width': width,
                                    'utilization': width / self.master_width,
                                    'composition': {width: 1},
                                    'waste': self.master_width - width
                                }
                                production_plan.append({
                                    'pattern': single_pattern['description'],
                                    'runs': quantity,
                                    'utilization': single_pattern['utilization'],
                                    'waste_per_coil': single_pattern['waste'],
                                    'composition': single_pattern['composition']
                                })
                                total_coils_used += quantity
                                total_waste += single_pattern['waste'] * quantity
                                remaining_orders[width] = 0
                        break
                
                if best_pattern:
                    production_plan.append({
                        'pattern': best_pattern['description'],
                        'runs': best_runs,
                        'utilization': best_pattern['utilization'],
                        'waste_per_coil': best_pattern['waste'],
                        'composition': best_pattern['composition']
                    })
                    
                    for width, count in best_pattern['composition'].items():
                        remaining_orders[width] -= count * best_runs
                    
                    total_coils_used += best_runs
                    total_waste += best_pattern['waste'] * best_runs
                    
                    # 移除已完成的规格
                    remaining_orders = {k: v for k, v in remaining_orders.items() if v > 0}
        
        utilization_rate = 1 - (total_waste / (total_coils_used * self.master_width)) if total_coils_used > 0 else 0
        
        return {
            'method': '贪心算法',
            'production_plan': production_plan,
            'total_coils': total_coils_used,
            'total_waste': total_waste,
            'utilization_rate': round(utilization_rate, 4),
            'remaining_orders': remaining_orders,
            'computation_time': round(time.time() - start_time, 2)
        }

# 主应用函数
def main():
    # 添加自定义CSS
    add_custom_css()
    
    # ==================== 页面顶部Logo和标题 ====================
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # 显示公司标题
        st.markdown('<div class="company-title">恒丰纸业</div>', unsafe_allow_html=True)
        
        # 尝试加载Logo（多种路径尝试）
        logo_paths = [
            "hengfeng_logo.png",           # 根目录
            "assets/hengfeng_logo.png",    # assets文件夹
            "images/hengfeng_logo.png",    # images文件夹
            "logo.png"                     # 通用名称
        ]
        
        logo_loaded = False
        for logo_path in logo_paths:
            try:
                st.image(logo_path, width=250)
                logo_loaded = True
                break
            except:
                continue
        
        if not logo_loaded:
            # 如果找不到Logo文件，显示文字替代
            st.markdown("""
            <div style="text-align: center; padding: 20px; border: 2px dashed #ccc; border-radius: 10px;">
                <h3>恒丰纸业</h3>
                <p>辊纸套切优化系统</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 应用主标题
    st.title("📊 辊纸套切优化系统")
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        本系统用于优化辊纸生产过程中的套切方案，通过智能算法计算最优排产计划，
        最大限度提高原材料利用率，减少浪费。
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== 侧边栏设置 ====================
    st.sidebar.markdown("## 🏢 恒丰纸业")
    
    # 侧边栏也可以显示小尺寸Logo
    with st.sidebar:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                st.image("hengfeng_logo.png", width=100)
            except:
                st.markdown("**恒丰纸业**")
    
    st.sidebar.header("参数设置")
    
    master_width = st.sidebar.number_input("母卷宽度 (mm)", min_value=1000, max_value=10000, value=5480)
    min_utilization = st.sidebar.slider("最低利用率阈值", min_value=0.7, max_value=0.99, value=0.9)
    
    # ==================== 订单输入部分 ====================
    st.header("📋 订单输入")
    
    # 添加示例选择
    example_option = st.selectbox(
        "选择示例数据或手动输入",
        ["手动输入", "示例1: 1810×51, 1715×86, 1860×26", "示例2: 1510×37, 1720×10, 1900×49", "示例3: 1810×10, 1660×11"]
    )
    
    if example_option == "示例1: 1810×51, 1715×86, 1860×26":
        default_orders = "1810,51\n1715,86\n1860,26"
    elif example_option == "示例2: 1510×37, 1720×10, 1900×49":
        default_orders = "1510,37\n1720,10\n1900,49"
    elif example_option == "示例3: 1810×10, 1660×11":
        default_orders = "1810,10\n1660,11"
    else:
        default_orders = ""
    
    col1, col2 = st.columns(2)
    
    with col1:
        order_input = st.text_area(
            "订单数据",
            height=200,
            value=default_orders,
            help="每行输入一个规格，格式：宽度(mm),数量"
        )
    
    with col2:
        st.markdown("""
        **输入示例：**
        ```
        1810,51
        1715,86
        1860,26
        ```
        
        **说明：**
        - 每行一个规格
        - 格式：宽度(mm),数量
        - 宽度为整数，数量为整数
        - 系统将确保完全消耗所有订单
        """)
    
    # ==================== 订单处理逻辑 ====================
    # 解析订单数据
    orders = {}
    try:
        for line in order_input.strip().split('\n'):
            if line.strip():
                width, quantity = line.strip().split(',')
                width_val = int(width)
                quantity_val = int(quantity)
                
                if width_val > master_width:
                    st.error(f"错误：规格宽度 {width_val}mm 超过母卷宽度 {master_width}mm，无法生产！")
                    st.stop()
                
                orders[width_val] = quantity_val
    except Exception as e:
        st.error(f"订单数据格式错误，请检查输入格式！错误: {str(e)}")
        st.stop()
    
    if not orders:
        st.warning("请输入订单数据")
        st.stop()
    
    # 显示订单摘要
    st.subheader("订单摘要")
    order_df = pd.DataFrame([(w, q) for w, q in orders.items()], columns=['宽度(mm)', '数量'])
    st.dataframe(order_df, use_container_width=True)
    
    # 初始化优化器
    optimizer = PaperCuttingOptimizer(master_width, min_utilization)
    
    # 生成可行方案
    with st.spinner("正在生成可行切割方案..."):
        patterns = optimizer.generate_patterns(list(orders.keys()))
    
    st.subheader("可行切割方案")
    st.write(f"共生成 {len(patterns)} 个可行方案")
    
    # 显示部分高效方案
    if patterns:
        top_patterns = patterns[:10]
        pattern_data = []
        for p in top_patterns:
            pattern_data.append({
                '方案': p['description'],
                '总宽度(mm)': p['total_width'],
                '利用率': f"{p['utilization']*100:.2f}%",
                '废料(mm)': p['waste']
            })
        
        patterns_df = pd.DataFrame(pattern_data)
        st.dataframe(patterns_df, use_container_width=True)
    else:
        st.error("未找到可行切割方案，请调整参数或订单数据！")
        st.stop()
    
    # 运行优化算法
    st.header("优化计算")
    
    if st.button("开始优化计算", type="primary"):
        with st.spinner("正在计算最优方案..."):
            result = optimizer.greedy_optimize(orders.copy())
        
        # 显示结果
        st.header("优化结果")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总生产车数", result['total_coils'])
        col2.metric("原料利用率", f"{result['utilization_rate']*100:.2f}%")
        col3.metric("总废料(mm·车)", result['total_waste'])
        col4.metric("计算时间(秒)", result['computation_time'])
        
        # 检查是否完全消耗了订单
        if result['remaining_orders']:
            st.error(f"⚠️ 未能完全消耗所有订单，剩余: {result['remaining_orders']}")
        else:
            st.success("✅ 所有订单已完全消耗！")
        
        # 生产计划表
        if result['production_plan']:
            st.subheader("生产计划详情")
            plan_df = pd.DataFrame(result['production_plan'])
            plan_df['总废料'] = plan_df['waste_per_coil'] * plan_df['runs']
            plan_df['利用率百分比'] = plan_df['utilization'].apply(lambda x: f"{x*100:.2f}%")
            
            display_cols = ['pattern', 'runs', '利用率百分比', 'waste_per_coil', '总废料']
            st.dataframe(plan_df[display_cols], use_container_width=True)
            
            # 创建可视化图表
            try:
                col1, col2 = st.columns(2)
                
                with col1:
                    # 利用率柱状图
                    fig_bar = px.bar(
                        plan_df, 
                        x='pattern', 
                        y=plan_df['utilization']*100,
                        title='各方案利用率 (%)',
                        labels={'y': '利用率 (%)', 'pattern': '切割方案'}
                    )
                    fig_bar.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                with col2:
                    # 废料饼图
                    if len(plan_df) > 1:
                        fig_pie = px.pie(
                            plan_df,
                            values='总废料',
                            names='pattern',
                            title='废料分布'
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.info("单一方案，无需显示废料分布图")
                        
            except Exception as e:
                st.warning(f"图表生成遇到问题: {str(e)}")
            
            # 添加下载功能
            csv = plan_df[display_cols].to_csv(index=False)
            st.download_button(
                label="下载生产计划CSV",
                data=csv,
                file_name="恒丰纸业_生产计划.csv",
                mime="text/csv"
            )
        
        # 经济效益估算
        st.subheader("经济效益估算")
        total_material = result['total_coils'] * master_width
        used_material = total_material - result['total_waste']
        waste_saving = result['total_waste'] / 1000  # 转换为米
        
        # 简化的成本计算
        cost_saving = waste_saving * 0.033 * (master_width/1000) * 6000 / 1000
        
        st.info(f"""
        - **总使用原料**: {used_material/1000:.1f} 米
        - **总废料**: {waste_saving:.1f} 米
        - **预计节约成本**: {cost_saving:.0f} 元 
        - **平均利用率**: {result['utilization_rate']*100:.1f}%
        """)
        
        # 添加使用建议
        st.subheader("生产建议")
        if result['utilization_rate'] > 0.95:
            st.success("🎉 优化效果优秀，建议按此方案生产")
        elif result['utilization_rate'] > 0.9:
            st.info("👍 优化效果良好，可以按此方案生产")
        else:
            st.warning("⚠️ 利用率偏低，建议调整订单组合或参数")
        
        # 页脚添加公司信息
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 14px;">
            <p>恒丰纸业有限公司 - 辊纸套切优化系统</p>
            <p>© 2024 恒丰纸业 版权所有</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
