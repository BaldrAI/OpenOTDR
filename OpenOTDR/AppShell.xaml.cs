namespace OpenOTDR
{
    public partial class AppShell : Shell
    {
        public AppShell()
        {
            InitializeComponent();
            if (DeviceInfo.Idiom == DeviceIdiom.Phone)
                Shell.Current.CurrentItem = PhoneTabs;

        }
    }
}
