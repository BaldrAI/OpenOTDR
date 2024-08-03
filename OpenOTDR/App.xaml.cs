using OpenOTDR.Services;

namespace OpenOTDR
{
    public partial class App : Application
    {
        public App()
        {
            InitializeComponent();
            Constants.ctx = new ProjectsContext();
            MainPage = new AppShell();
        }

        ~App()
        {
            Constants.ctx.SaveChanges();
            Constants.ctx.Dispose();
        }
    }
}
