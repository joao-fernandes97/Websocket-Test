using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Toggles the ConnectionSettingsUI panel open/closed.
/// </summary>
[RequireComponent(typeof(Button))]
public class ConnectionSettingsPanelToggle : MonoBehaviour
{
    [SerializeField] private GameObject _panel;
    [SerializeField] private Image      _buttonIcon;
    [SerializeField] private Sprite     _openIcon;
    [SerializeField] private Sprite     _closeIcon;
    [SerializeField] private KeyCode    _toggleKey = KeyCode.Escape;

    private void Awake()
    {
        GetComponent<Button>().onClick.AddListener(Toggle);

        // Sync icon to whatever state the panel starts in.
        UpdateIcon();
    }

    private void Update()
    {
        if (Input.GetKeyDown(_toggleKey))
            Toggle();
    }

    private void Toggle()
    {
        _panel.SetActive(!_panel.activeSelf);
        UpdateIcon();
    }

    private void UpdateIcon()
    {
        if (_buttonIcon == null) return;
        _buttonIcon.sprite = _panel.activeSelf ? _closeIcon : _openIcon;
    }
}