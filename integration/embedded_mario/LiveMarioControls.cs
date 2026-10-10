using System;
using System.Buffers.Binary;
using System.Diagnostics;
using System.Threading;
using ImGuiNET;
using Silk.NET.Input;
using RecompOne.Runtime.Config;
using RecompOne.Runtime.Host.Window;
using RecompOne.Runtime.Events;
using RecompOne.Runtime.Catalogs;
using RecompOne.Runtime.Memory;

internal static class LiveMarioControls
{
    sealed record Scene(long Timestamp, uint Level, bool Valid, int Epoch);
    static Scene scene = new(0, 0, false, 0);
    static LiveMarioInput input = new();
    static int uiThread;
    static volatile bool running;
    static readonly System.Reflection.PropertyInfo inputAllowed = typeof(MenuRegistry).Assembly
        .GetType("RecompOne.Runtime.Host.Window.OriginalMarioInputHost")?.GetProperty("InputAllowed");
    internal static LiveMarioInput Input => input;
    internal static bool IsRunning => running;
    internal static bool SceneValid(long now)
    {
        var current = Volatile.Read(ref scene);
        return current.Valid && current.Epoch == input.Latest.Epoch &&
            now >= current.Timestamp && now - current.Timestamp <= Stopwatch.Frequency / 4;
    }
    internal static void VerifyHost()
    {
        if (inputAllowed == null) throw new InvalidOperationException("M43 private input host missing");
    }
    internal static void Start()
    {
        input = new();
        scene = new(0, 0, false, 0);
        uiThread = 0;
        running = true;
        Event.AddListener<PadReadEvent>(ObserveScene);
    }
    internal static void Stop()
    {
        running = false;
        Event.RemoveListener<PadReadEvent>(ObserveScene);
        input.Publish(Stopwatch.GetTimestamp(), 0, false, false, false, false, false, false);
    }
    static void ObserveScene(PadReadEvent host)
    {
        if (!running || host.Port != 0) return;
        var previous = Volatile.Read(ref scene);
        uint level = 0;
        bool valid = false;
        try
        {
        if (host.Memory is PSMemory memory && memory.Ram.Length == 0x200000 &&
            Catalog.LevelIdAddr == 0x80056710u)
        {
            ReadOnlySpan<byte> ram = memory.Ram;
            level = BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice(0x56710, 4));
            valid = Catalog.Levels.TryGet(level, out var info) && info.Kind == LevelKind.Gameplay &&
                BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice(0x56400, 4)) == 0 &&
                BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice(0x5640C, 4)) == 0;
        }
        }
        catch { valid = false; }
        int epoch = previous.Epoch + (level != previous.Level || valid != previous.Valid ? 1 : 0);
        Volatile.Write(ref scene, new Scene(Stopwatch.GetTimestamp(), level, valid, epoch));
    }
    internal static void Capture()
    {
        if (!running) return;
        int current = Environment.CurrentManagedThreadId;
        if (uiThread == 0) uiThread = current;
        if (uiThread != current) throw new InvalidOperationException("Mario input UI owner changed");
        var currentScene = Volatile.Read(ref scene);
        long now = Stopwatch.GetTimestamp();
        var io = ImGui.GetIO();
        if (ImGui.IsItemHovered() && ImGui.IsMouseClicked(ImGuiMouseButton.Left))
            ImGui.SetWindowFocus();
        bool active = inputAllowed?.GetValue(null) is true && !io.AppFocusLost && !io.WantTextInput &&
            ImGui.IsWindowFocused() && !ImGui.IsPopupOpen("", ImGuiPopupFlags.AnyPopupId) &&
            currentScene.Valid && now - currentScene.Timestamp <= Stopwatch.Frequency / 4 &&
            BindingsSafe();
        input.Publish(now, currentScene.Epoch, active, ImGui.IsKeyDown(ImGuiKey.J),
            ImGui.IsKeyDown(ImGuiKey.L), ImGui.IsKeyDown(ImGuiKey.I),
            ImGui.IsKeyDown(ImGuiKey.K), ImGui.IsKeyDown(ImGuiKey.U));
    }
    static bool Reserved(Key key) => key is Key.I or Key.J or Key.K or Key.L or Key.U;
    static bool BindingsSafe()
    {
        foreach (var bindings in new[] { ConfigManager.Game.Keys, ConfigManager.Game.Keys2 })
        {
            if (bindings == null) return false;
            foreach (var property in typeof(KeyBindings).GetProperties())
            {
                if (property.PropertyType != typeof(string)) return false;
                var name = (string)property.GetValue(bindings);
                if (string.IsNullOrWhiteSpace(name)) continue;
                if (!KeyBindingNames.TryParse(name, out _) || KeyBindingNames.AnyPressed(name, Reserved))
                    return false;
            }
        }
        string cheat = ConfigManager.View.CheatMenuKey;
        return string.IsNullOrWhiteSpace(cheat) ||
            (KeyBindingNames.TryParse(cheat, out var key) && !Reserved(key));
    }
}
