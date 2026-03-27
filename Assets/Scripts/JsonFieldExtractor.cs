using System.Text.RegularExpressions;
using UnityEngine;

/// <summary>
/// Lightweight helpers for pulling individual fields out of a JSON string
/// without needing to declare a dedicated [Serializable] class for every endpoint.
/// </summary>
public static class JsonFieldExtractor
{
    /// <summary>Extract a float value by field name, e.g. {"bpm":72.5} → 72.5</summary>
    public static bool TryGetFloat(string json, string fieldName, out float value)
    {
        value = 0f;
        // matches  "fieldName"   :   123.45  or  -0.5
        var pattern = $@"""{Regex.Escape(fieldName)}""\s*:\s*(-?\d+(?:\.\d+)?)";
        var match   = Regex.Match(json, pattern);
        if (!match.Success) return false;
        return float.TryParse(match.Groups[1].Value,
            System.Globalization.NumberStyles.Float,
            System.Globalization.CultureInfo.InvariantCulture,
            out value);
    }

    /// <summary>Extract a string value by field name, e.g. {"status":"ok"} → "ok"</summary>
    public static bool TryGetString(string json, string fieldName, out string value)
    {
        value = string.Empty;
        var pattern = $@"""{Regex.Escape(fieldName)}""\s*:\s*""([^""]*)""";
        var match   = Regex.Match(json, pattern);
        if (!match.Success) return false;
        value = match.Groups[1].Value;
        return true;
    }

    /// <summary>Extract an int value by field name.</summary>
    public static bool TryGetInt(string json, string fieldName, out int value)
    {
        value = 0;
        var pattern = $@"""{Regex.Escape(fieldName)}""\s*:\s*(-?\d+)";
        var match   = Regex.Match(json, pattern);
        if (!match.Success) return false;
        return int.TryParse(match.Groups[1].Value, out value);
    }

    /// <summary>Extract a bool value by field name.</summary>
    public static bool TryGetBool(string json, string fieldName, out bool value)
    {
        value = false;
        var pattern = $@"""{Regex.Escape(fieldName)}""\s*:\s*(true|false)";
        var match   = Regex.Match(json, pattern, RegexOptions.IgnoreCase);
        if (!match.Success) return false;
        value = match.Groups[1].Value.ToLower() == "true";
        return true;
    }
}