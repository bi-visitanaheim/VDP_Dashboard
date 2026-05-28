# =============================================================================
# Copyright (c) 2026 Wilton John Picou, GloCon Solutions LLC.
# All rights reserved. Proprietary and confidential.
#
# Authored, developed, and owned solely by Wilton John Picou of GloCon
# Solutions LLC. Licensed exclusively and perpetually to Visit Dana Point as
# the sole authorized user. No part of this software may be copied, reproduced,
# modified, published, distributed, sublicensed, or used by any other person or
# entity without the prior express written consent of the copyright holder.
# Unauthorized use, reproduction, or distribution is strictly prohibited and
# constitutes a violation of U.S. and international copyright law
# (17 U.S.C. Sec. 101 et seq.).
#
# Attribution to "Wilton John Picou, GloCon Solutions LLC" must be retained.
# See the LICENSE file at the repository root for the full, binding terms.
# =============================================================================

from scripts.data_access import load_str_daily, load_str_monthly
import streamlit as st

df_daily = load_str_daily()
df_monthly = load_str_monthly()

# Example usage
daily_revpar = (
    df_daily[df_daily["metric_name"] == "revpar"]
    .sort_values("asofdate")
)

monthly_revpar = (
    df_monthly[df_monthly["metric_name"] == "revpar"]
    .sort_values("asofdate")
)

st.subheader("Daily RevPAR")
st.line_chart(daily_revpar.set_index("asofdate")["metric_value"])

st.subheader("Monthly RevPAR")
st.line_chart(monthly_revpar.set_index("asofdate")["metric_value"])

