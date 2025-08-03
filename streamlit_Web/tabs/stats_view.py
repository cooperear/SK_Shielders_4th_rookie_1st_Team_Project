# ==============================================================================
# stats_view.py - 통계 차트 탭 (개선된 버전)
# ==============================================================================
# 이 파일은 사용자가 유기동물 데이터의 핵심적인 인사이트를 한눈에 파악할 수 있도록,
# 직관적이고 의미 있는 통계 차트를 제공합니다.
#
# [개선된 분석 흐름]
# 1. **핵심 현황 요약:** 전체 데이터의 가장 중요한 특징(축종, 품종, 나이)을 요약합니다.
# 2. **시간 및 지역 기반 분석:** 시간(월별)과 공간(지역별)에 따른 패턴을 심층적으로 분석합니다.
# 3. **기타 주요 통계:** 그 외 유의미한 정보(요일별, 상태별)를 제공합니다.
# ==============================================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import numpy as np

def show(final_animals, filtered_shelters):
    """
    '통계 차트' 탭의 전체 UI를 그리고 로직을 처리하는 메인 함수입니다.
    """
    st.subheader("📊 핵심 통계 대시보드")
    st.info("필터링된 데이터를 바탕으로 유기동물의 주요 현황과 패턴을 분석합니다.")

    if final_animals.empty:
        st.warning("표시할 동물 데이터가 없습니다. 필터 조건을 변경해보세요.")
        return

    # --- 0. 데이터 전처리 ---
    df = final_animals.copy()
    df['notice_date'] = pd.to_datetime(df['notice_date'], errors='coerce')
    
    # 나이(age) 숫자형으로 변환
    df['age_str'] = df['age'].astype(str)
    df['birth_year'] = pd.to_numeric(df['age_str'].str.extract(r'(\d{4})')[0], errors='coerce')
    current_year = datetime.now().year
    df['age_numeric'] = current_year - df['birth_year']
    df.loc[df['age_numeric'] > 80, 'age_numeric'] = np.nan # 비현실적인 나이 제거

    # --- 1. 핵심 현황 요약 ---
    st.markdown("---")
    st.markdown("### Ⅰ. 주요 현황 요약")

    # 1-1. 축종별 보호 동물 비율
    st.markdown("#### 1. 축종별 보호 동물 비율")
    species_chart_data = df.groupby("upkind_name").size().reset_index(name='count')
    fig_donut_species = px.pie(
        species_chart_data, names="upkind_name", values="count", hole=0.4,
        color="upkind_name", color_discrete_map={'개': '#FFA07A', '고양이': '#87CEFA', '기타': '#90EE90'}
    )
    fig_donut_species.update_traces(textinfo='percent+label', pull=[0.05, 0.05, 0.05])
    fig_donut_species.update_layout(showlegend=True, margin=dict(t=10, b=10), legend_title_text='축종')
    st.plotly_chart(fig_donut_species, use_container_width=True)

    # 1-2. 나이대별 보호 현황 및 입양률
    st.markdown("#### 2. 나이대별 보호 현황 및 입양률")
    if df['age_numeric'].notna().any():
        bins = [0, 1, 3, 8, df['age_numeric'].max() + 1]
        labels = ['1살 미만', '1-3살', '4-7살', '8살 이상']
        df['age_group'] = pd.cut(df['age_numeric'], bins=bins, labels=labels, right=False)

        age_group_stats = df.groupby('age_group').agg(
            total_count=('desertion_no', 'size'),
            adopted_count=('process_state', lambda x: (x == '종료(입양)').sum())
        ).reset_index()
        age_group_stats['adoption_rate'] = (age_group_stats['adopted_count'] / age_group_stats['total_count'] * 100).round(1)

        fig_age = make_subplots(specs=[[{"secondary_y": True}]])
        fig_age.add_trace(
            go.Bar(x=age_group_stats['age_group'], y=age_group_stats['total_count'], name='보호 수', marker_color='lightblue'),
            secondary_y=False,
        )
        fig_age.add_trace(
            go.Scatter(x=age_group_stats['age_group'], y=age_group_stats['adoption_rate'], name='입양률', marker_color='crimson'),
            secondary_y=True,
        )
        fig_age.update_layout(title_text="나이대별 보호 수 및 입양률", template='plotly_white', margin=dict(t=50, b=10))
        fig_age.update_yaxes(title_text="보호 수 (마리)", secondary_y=False)
        fig_age.update_yaxes(title_text="입양률 (%)", secondary_y=True)
        st.plotly_chart(fig_age, use_container_width=True)
    else:
        st.info("나이 데이터가 부족하여 분석할 수 없습니다.")

    # 1-3. 품종별 보호 현황 (개선된 복합 차트)
    st.markdown("#### 3. 품종별 보호 현황 Top 10")
    if 'kind_name' in df.columns and not df['kind_name'].empty:
        top_10_kinds = df['kind_name'].value_counts().nlargest(10).index
        df_top_10 = df[df['kind_name'].isin(top_10_kinds)]

        kind_stats = df_top_10.groupby('kind_name').agg(
            total_count=('desertion_no', 'size'),
            adopted_count=('process_state', lambda x: (x == '종료(입양)').sum())
        ).reset_index()
        kind_stats['adoption_rate'] = (kind_stats['adopted_count'] / kind_stats['total_count'] * 100).round(1)
        kind_stats = kind_stats.sort_values('total_count', ascending=False)

        fig_kind = make_subplots(specs=[[{"secondary_y": True}]])
        fig_kind.add_trace(
            go.Bar(x=kind_stats['kind_name'], y=kind_stats['total_count'], name='보호 수', marker_color='lightgreen'),
            secondary_y=False,
        )
        fig_kind.add_trace(
            go.Scatter(x=kind_stats['kind_name'], y=kind_stats['adoption_rate'], name='입양률', marker_color='purple'),
            secondary_y=True,
        )
        fig_kind.update_layout(title_text="상위 10개 품종의 보호 수 및 입양률", template='plotly_white', margin=dict(t=50, b=10))
        fig_kind.update_yaxes(title_text="보호 수 (마리)", secondary_y=False)
        fig_kind.update_yaxes(title_text="입양률 (%)", secondary_y=True)
        st.plotly_chart(fig_kind, use_container_width=True)
    else:
        st.info("세부 품종 데이터가 없습니다.")

    # --- 2. 시간 및 지역 기반 분석 ---
    st.markdown("---")
    st.markdown("### Ⅱ. 시간 및 지역별 심층 분석")

    # 2-1. 월별 입양률 추이
    st.markdown("#### 4. 월별 입양률 추이")
    if 'notice_date' in df.columns and not df['notice_date'].empty:
        adoption_df = df.copy()
        adoption_df['month'] = adoption_df['notice_date'].dt.to_period('M').dt.to_timestamp()
        monthly_stats = adoption_df.groupby('month').agg(
            total=('desertion_no', 'size'),
            adopted=('process_state', lambda x: (x == '종료(입양)').sum())
        ).reset_index()
        monthly_stats['adoption_rate'] = monthly_stats.apply(
            lambda row: (row['adopted'] / row['total'] * 100) if row['total'] > 0 else 0, axis=1
        )
        fig_adoption_trend = px.line(
            monthly_stats, x='month', y='adoption_rate', markers=True, template='plotly_white',
            labels={'month': '월', 'adoption_rate': '입양률 (%)'}
        )
        fig_adoption_trend.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig_adoption_trend, use_container_width=True)
    else:
        st.info("공고일 데이터가 없어 입양률 추이를 표시할 수 없습니다.")

    # 2-2. 지역별 월별 발생 건수 (히트맵)
    st.markdown("#### 5. 지역별 월별 발생 건수 (상위 10개 지역)")
    if not filtered_shelters.empty:
        merged_data = pd.merge(df, filtered_shelters, on='shelter_name', how='left')
        if 'region' in merged_data.columns and not merged_data['region'].empty:
            top_regions = merged_data['region'].value_counts().nlargest(10).index
            df_top_regions = merged_data[merged_data['region'].isin(top_regions)].copy()
            df_top_regions['month'] = df_top_regions['notice_date'].dt.month
            region_month_counts = df_top_regions.groupby(['region', 'month']).size().unstack(fill_value=0).reindex(columns=range(1, 13), fill_value=0)
            
            fig_heatmap = px.imshow(
                region_month_counts, labels=dict(x="월", y="지역명", color="발생 건수"),
                x=[f'{i}월' for i in range(1, 13)], y=region_month_counts.index,
                text_auto=True, aspect="auto", color_continuous_scale='YlGnBu'
            )
            fig_heatmap.update_layout(title_text='월별 유기동물 발생 건수 히트맵', title_x=0.5, margin=dict(t=50, b=10))
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("지역(region) 데이터가 없어 히트맵을 표시할 수 없습니다.")
    else:
        st.info("보호소 데이터가 부족하여 지역별 분석을 수행할 수 없습니다.")

    # 2-3. 지역별 성별 발생 비율 (스택 바 차트)
    st.markdown("#### 6. 지역별 성별 발생 비율 (상위 10개 지역)")
    if not filtered_shelters.empty:
        merged_data = pd.merge(df, filtered_shelters, on='shelter_name', how='left')
        if 'region' in merged_data.columns and 'sex' in merged_data.columns:
            top_regions = merged_data['region'].value_counts().nlargest(10).index
            df_top_regions = merged_data[merged_data['region'].isin(top_regions)].copy()
            region_sex_counts = df_top_regions.groupby(['region', 'sex']).size().unstack(fill_value=0)
            region_sex_proportions = region_sex_counts.div(region_sex_counts.sum(axis=1), axis=0)

            fig_stacked_bar = px.bar(
                region_sex_proportions, x=region_sex_proportions.index, y=region_sex_proportions.columns,
                labels={"x": "지역명", "y": "비율", "color": "성별"}, template='plotly_white', barmode='stack'
            )
            fig_stacked_bar.update_layout(title_text='상위 10개 지역별 성별 발생 비율', title_x=0.5, yaxis_tickformat='.0%')
            st.plotly_chart(fig_stacked_bar, use_container_width=True)
        else:
            st.info("지역(region) 또는 성별(sex) 데이터가 없어 분석할 수 없습니다.")
    else:
        st.info("보호소 데이터가 부족하여 지역별 분석을 수행할 수 없습니다.")

    # --- 3. 기타 주요 통계 ---
    st.markdown("---")
    st.markdown("### Ⅲ. 기타 주요 통계")

    # 3-1. 요일별 유기동물 발생 추이
    st.markdown("#### 7. 요일별 유기동물 발생 추이")
    if 'notice_date' in df.columns and not df['notice_date'].empty:
        df_dow = df.copy()
        df_dow['day_of_week'] = df_dow['notice_date'].dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_counts = df_dow.groupby('day_of_week').size().reindex(day_order).reset_index(name='count')
        fig_dow = px.bar(dow_counts, x='day_of_week', y='count', text='count', template="plotly_white")
        fig_dow.update_traces(textposition="outside")
        fig_dow.update_layout(xaxis_title="요일", yaxis_title="발생 건수", margin=dict(t=10, b=10))
        st.plotly_chart(fig_dow, use_container_width=True)
    else:
        st.info("공고일 데이터가 없어 요일별 추이를 표시할 수 없습니다.")

    # 3-2. 처리 상태별 보호 동물 수
    st.markdown("#### 8. 처리 상태별 보호 동물 수")
    if 'process_state' in df.columns and not df['process_state'].empty:
        process_state_chart_data = df.groupby("process_state").size().reset_index(name='count')
        fig_process_state = px.bar(
            process_state_chart_data.sort_values('count', ascending=True),
            x="count", y="process_state", color="process_state", text="count",
            orientation='h', template="plotly_white"
        )
        fig_process_state.update_traces(textposition="outside")
        fig_process_state.update_layout(showlegend=False, margin=dict(t=10, b=10), yaxis_title=None, xaxis_title="발생 건수")
        st.plotly_chart(fig_process_state, use_container_width=True)
    else:
        st.info("처리 상태 데이터가 없습니다.")