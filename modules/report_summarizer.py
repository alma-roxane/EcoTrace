# modules/report_summarizer.py
# Summarizes sustainability reports with key metrics and findings

from typing import Dict, Optional


def summarize_report(data_dict: Dict) -> Optional[Dict]:
    """
    Summarizes the uploaded sustainability report with key information.
    
    Args:
        data_dict: Dictionary containing parsed report data with keys like:
                   scope1_tco2e, scope2_cbam_tco2e, electricity_mwh, 
                   urea_production_mt, year, narrative_text
    
    Returns:
        dict with keys: 'executive_summary', 'key_metrics', 'emissions_overview'
    """
    
    if not data_dict:
        return None
    
    try:
        # Extract key data points
        year = data_dict.get("year", "Unknown")
        scope1 = float(data_dict.get("scope1_tco2e") or 0)
        scope2 = float(data_dict.get("scope2_cbam_tco2e") or data_dict.get("scope2_reported_tco2e") or 0)
        production = float(data_dict.get("urea_production_mt") or 1)
        electricity = float(data_dict.get("electricity_mwh") or 0)
        narrative = data_dict.get("narrative_text", "")
        
        # Calculate metrics
        total_emissions = scope1 + scope2
        emissions_intensity = total_emissions / max(production, 1)
        
        # Build emissions overview
        emissions_overview = f"""
        • **Reporting Year**: {year}
        • **Scope 1 Emissions**: {scope1:,.0f} tCO₂e
        • **Scope 2 Emissions**: {scope2:,.0f} tCO₂e
        • **Total Emissions**: {total_emissions:,.0f} tCO₂e
        • **Production Volume**: {production:,.0f} tonnes
        • **Emissions Intensity**: {emissions_intensity:.2f} tCO₂e per tonne
        • **Electricity Consumption**: {electricity:,.0f} MWh
        """
        
        # Build executive summary based on emissions
        if total_emissions > 100000:
            risk_level = "HIGH"
            summary_text = f"This report indicates significant emissions with {total_emissions:,.0f} tCO₂e across both scopes. The organization's carbon footprint of {emissions_intensity:.2f} tCO₂e per unit of production suggests considerable environmental impact that warrants immediate mitigation strategies."
        elif total_emissions > 50000:
            risk_level = "MEDIUM"
            summary_text = f"The reported emissions of {total_emissions:,.0f} tCO₂e demonstrate moderate environmental impact. With an emissions intensity of {emissions_intensity:.2f} tCO₂e per tonne, there are clear opportunities for improvement through energy efficiency and renewable energy adoption."
        else:
            risk_level = "LOW"
            summary_text = f"The organization has reported relatively lower emissions of {total_emissions:,.0f} tCO₂e. With an emissions intensity of {emissions_intensity:.2f} tCO₂e per tonne, the current operations show good emissions management practices."
        
        # Extract key insights from narrative if available
        key_insights = _extract_key_insights(narrative)
        
        # Build narrative summary
        narrative_summary = ""
        if narrative and len(narrative) > 50:
            narrative_summary = narrative[:300] + "..." if len(narrative) > 300 else narrative
        else:
            narrative_summary = "No detailed narrative provided in the report."
        
        return {
            "executive_summary": f"**Risk Level: {risk_level}**\n\n{summary_text}",
            "key_metrics": emissions_overview,
            "emissions_overview": emissions_overview,
            "risk_level": risk_level,
            "key_insights": key_insights,
            "narrative_summary": narrative_summary,
            "total_emissions": total_emissions,
            "emissions_intensity": emissions_intensity
        }
        
    except Exception as e:
        print(f"[Report Summarizer] ERROR during summarization: {e}")
        return {
            "executive_summary": "Unable to generate summary. Please check the uploaded report format.",
            "key_metrics": "Data extraction failed.",
            "emissions_overview": "Please verify the report data."
        }


def _extract_key_insights(narrative_text: str) -> str:
    """
    Extracts key insights from the narrative text.
    
    Args:
        narrative_text: The narrative section of the report
    
    Returns:
        str: Key insights extracted from the narrative
    """
    
    if not narrative_text or len(narrative_text) < 50:
        return "• No significant narrative insights available"
    
    text_lower = narrative_text.lower()
    insights = []
    
    # Check for renewable energy initiatives
    if any(word in text_lower for word in ["renewable", "solar", "wind", "hydro"]):
        insights.append("• Renewable energy initiatives are being pursued")
    
    # Check for emission reduction targets
    if any(word in text_lower for word in ["target", "reduction", "goal", "commit"]):
        insights.append("• Organization has set emissions reduction targets")
    
    # Check for energy efficiency
    if any(word in text_lower for word in ["efficiency", "efficient", "optimize", "improvement"]):
        insights.append("• Energy efficiency improvements are underway")
    
    # Check for waste management
    if any(word in text_lower for word in ["waste", "recycl", "circular", "reuse"]):
        insights.append("• Waste management and circular economy practices present")
    
    # Check for sustainability certification
    if any(word in text_lower for word in ["iso", "cert", "standard", "verified"]):
        insights.append("• Sustainability certifications and standards in place")
    
    # Check for supply chain focus
    if any(word in text_lower for word in ["supply chain", "supplier", "procurement"]):
        insights.append("• Supply chain sustainability is a priority")
    
    if not insights:
        insights.append("• Standard sustainability reporting practices")
        insights.append("• Environmental responsibility measures in place")
    
    return "\n".join(insights[:4])  # Return top 4 insights
