namespace RecompOne.Runtime.Host.Window;

public static class OriginalMarioInputHost
{
    public static bool InputAllowed => HostWindow.IsInputActive &&
        PanelManager.Get<PauseMenuPopup>()?.IsOpen != true;
}
