# modules/insight_generator.py
# AI-based insight generation using pretrained Hugging Face transformers
# Generates human-readable sustainability insights from extracted emissions data
# Uses FLAN-T5 for zero-shot instruction following

import os
from typing import Dict, Optional, Tuple

# Global model cache to avoid reloading on every request
_MODEL_CACHE = {
    "model": None,
    "tokenizer": None,
    "device": None
}


def _load_model_once():
    """
    Loads the transformer model and tokenizer once and caches it.
    Uses google/flan-t5-base: lightweight, fast, and excellent for instruction-following.
    
    Returns:
        tuple: (model, tokenizer, device)
    """
    if _MODEL_CACHE["model"] is not None:
        return _MODEL_CACHE["model"], _MODEL_CACHE["tokenizer"], _MODEL_CACHE["device"]
    
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch
        
        print("[Insight Generator] Loading pretrained model: google/flan-t5-base...")
        
        # Determine device (GPU if available, else CPU)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Insight Generator] Using device: {device}")
        
        # Load tokenizer and model
        model_name = "google/flan-t5-base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        model.to(device)
        model.eval()
        
        # Cache the loaded model
        _MODEL_CACHE["model"] = model
        _MODEL_CACHE["tokenizer"] = tokenizer
        _MODEL_CACHE["device"] = device
        
        print("[Insight Generator] Model loaded successfully and cached.")
        return model, tokenizer, device
        
    except Exception as e:
        print(f"[Insight Generator] ERROR loading model: {e}")
        return None, None, None


def _build_prompt(data_dict: Dict) -> str:
    """
    Converts structured emissions data into a natural language prompt
    for the AI model to analyze.
    
    Args:
        data_dict: Dictionary containing emissions data with keys like:
                   scope1_tco2e, scope2_cbam_tco2e, electricity_mwh, urea_production_mt
    
    Returns:
        str: A well-formatted prompt for the AI model
    """
    # Extract values with graceful fallback for missing data
    scope1 = data_dict.get("scope1_tco2e") or data_dict.get("scope1", 0)
    scope2 = data_dict.get("scope2_cbam_tco2e") or data_dict.get("scope2_reported_tco2e") or data_dict.get("scope2", 0)
    electricity = data_dict.get("electricity_mwh") or data_dict.get("electricity", "unknown")
    production = data_dict.get("urea_production_mt") or data_dict.get("production", 1)
    year = data_dict.get("year", "reporting period")
    
    # Format values safely
    try:
        scope1 = float(scope1) if scope1 not in (None, "unknown") else 0
        scope2 = float(scope2) if scope2 not in (None, "unknown") else 0
        electricity = float(electricity) if electricity not in (None, "unknown") else 0
        production = float(production) if production not in (None, "unknown") else 1
    except (ValueError, TypeError):
        scope1, scope2, electricity, production = 0, 0, 0, 1
    
    # Calculate emissions intensity
    intensity = (scope1 + scope2) / max(production, 1.0)
    
    # Build the prompt
    prompt = f"""Analyze the following sustainability emissions data and provide a concise, actionable insight (2-3 sentences max):

Emissions Data ({year}):
- Scope 1 Emissions: {scope1:,.0f} tCO2e
- Scope 2 Emissions (Grid): {scope2:,.0f} tCO2e
- Total Emissions: {scope1 + scope2:,.0f} tCO2e
- Production Volume: {production:,.0f} tonnes
- Emissions Intensity: {intensity:.2f} tCO2e per tonne

Provide a brief, actionable sustainability insight focusing on:
1. Key emission sources
2. One recommendation for improvement

Keep response to 2-3 sentences maximum."""
    
    return prompt


def _generate_insight_from_model(prompt: str, max_length: int = 150) -> Optional[str]:
    """
    Passes the prompt to the transformer model and generates an insight.
    
    Args:
        prompt: The input prompt for the model
        max_length: Maximum length of generated output (default 150 tokens)
    
    Returns:
        str: Generated insight, or None if generation fails
    """
    try:
        model, tokenizer, device = _load_model_once()
        
        if model is None or tokenizer is None:
            print("[Insight Generator] Model not available. Using fallback insight.")
            return None
        
        # Tokenize input
        inputs = tokenizer.encode(prompt, return_tensors="pt").to(device)
        
        # Generate output with optimized parameters for fast inference
        outputs = model.generate(
            inputs,
            max_length=max_length,
            min_length=20,
            num_beams=2,  # Beam search for better quality, light on compute
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            early_stopping=True
        )
        
        # Decode the generated text
        insight = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return insight.strip()
        
    except Exception as e:
        print(f"[Insight Generator] ERROR during generation: {e}")
        return None


def _generate_rule_based_insight(data_dict: Dict) -> str:
    """
    Fallback rule-based insight generation when AI model fails or is unavailable.
    Provides deterministic, consistent insights based on simple heuristics.
    
    Args:
        data_dict: Dictionary containing emissions data
    
    Returns:
        str: A rule-based sustainability insight
    """
    try:
        scope1 = float(data_dict.get("scope1_tco2e", 0) or 0)
        scope2 = float(data_dict.get("scope2_cbam_tco2e", data_dict.get("scope2_reported_tco2e", 0)) or 0)
        production = float(data_dict.get("urea_production_mt", 1) or 1)
        
        total_emissions = scope1 + scope2
        intensity = total_emissions / max(production, 1.0)
        scope2_ratio = scope2 / max(total_emissions, 1.0)
        
        # Rule 1: Check if Scope 2 dominates
        if scope2_ratio > 0.7:
            return f"Scope 2 (grid electricity) accounts for {scope2_ratio*100:.0f}% of emissions. Prioritize renewable energy sourcing and energy efficiency improvements to reduce grid dependency."
        
        # Rule 2: Check emissions intensity
        if intensity > 3.0:
            return f"Emissions intensity of {intensity:.2f} tCO2e/t is above EU baseline. Investigate operational efficiency and consider switching to cleaner energy sources to improve competitiveness under CBAM."
        
        # Rule 3: Check Scope 1 dominance
        if scope1 > scope2:
            return f"Scope 1 direct emissions ({scope1:,.0f} tCO2e) are the primary source. Focus on process optimization, waste reduction, and renewable heat integration to lower direct emissions."
        
        # Rule 4: Balanced emissions (default positive message)
        return f"Total emissions of {total_emissions:,.0f} tCO2e represent a {intensity:.2f} tCO2e/t intensity. Continue monitoring and pursue efficiency gains in both direct operations and energy procurement."
        
    except Exception as e:
        print(f"[Insight Generator] ERROR in rule-based fallback: {e}")
        return "Unable to generate sustainability insight. Please verify emissions data."


def generate_ai_insight(data_dict: Dict) -> str:
    """
    Main function: Generates AI-based sustainability insights from emissions data.
    
    This function:
    1. Converts structured emissions data into a natural language prompt
    2. Loads a pretrained FLAN-T5 model (cached for performance)
    3. Generates a concise, actionable insight using the transformer
    4. Falls back to rule-based logic if AI model fails
    
    Args:
        data_dict: Dictionary containing emissions data with keys like:
                   - scope1_tco2e: Scope 1 emissions in tCO2e
                   - scope2_cbam_tco2e: Scope 2 CBAM-compliant emissions
                   - scope2_reported_tco2e: Reported Scope 2 (alternate key)
                   - electricity_mwh: Electricity consumption in MWh
                   - urea_production_mt: Production volume in tonnes
                   - year: Reporting year
    
    Returns:
        str: A 2-3 sentence AI-generated sustainability insight
    
    Example:
        >>> data = {
        ...     "scope1_tco2e": 224845,
        ...     "scope2_cbam_tco2e": 15800,
        ...     "electricity_mwh": 16347,
        ...     "urea_production_mt": 250000,
        ...     "year": 2023
        ... }
        >>> insight = generate_ai_insight(data)
        >>> print(insight)
        "Scope 1 emissions dominate at 224845 tCO2e, with Scope 2 contributing only 15800 tCO2e.
         This suggests efficiency in electricity procurement. Focus on process improvements and
         renewable heat to further reduce direct emissions."
    """
    
    print("\n[Insight Generator] Generating sustainability insight...")
    
    # Validate input
    if not isinstance(data_dict, dict) or not data_dict:
        print("[Insight Generator] Empty or invalid data dictionary. Using default insight.")
        return "No emissions data available for analysis."
    
    # Build prompt from structured data
    prompt = _build_prompt(data_dict)
    print(f"[Insight Generator] Prompt prepared ({len(prompt)} chars)")
    
    # Try to generate using AI model
    insight = _generate_insight_from_model(prompt)
    
    # If AI generation fails, fall back to rule-based insight
    if insight is None:
        print("[Insight Generator] Falling back to rule-based insight generation...")
        insight = _generate_rule_based_insight(data_dict)
    
    print(f"[Insight Generator] Insight generated: {insight[:100]}...")
    return insight


def clear_model_cache():
    """
    Clears the cached model to free up memory.
    Use this if memory is constrained or after long sessions.
    """
    global _MODEL_CACHE
    _MODEL_CACHE["model"] = None
    _MODEL_CACHE["tokenizer"] = None
    _MODEL_CACHE["device"] = None
    print("[Insight Generator] Model cache cleared.")


if __name__ == "__main__":
    # Example usage for testing
    test_data = {
        "scope1_tco2e": 224845,
        "scope2_cbam_tco2e": 15800,
        "electricity_mwh": 16347,
        "urea_production_mt": 250000,
        "year": 2023
    }
    
    print("Testing insight generator...")
    insight = generate_ai_insight(test_data)
    print(f"\nGenerated Insight:\n{insight}")
