using Microsoft.EntityFrameworkCore;
using OpenOTDR.Models;
using Location = OpenOTDR.Models.Location;
using Contact = OpenOTDR.Models.Contact;
namespace OpenOTDR.Services;

public class ProjectsContext : DbContext
{
    public DbSet<Project> Projects { get; set; }
    public DbSet<Contact> Contacts { get; set; }
    public DbSet<Customer> Customers { get; set; }
    public DbSet<Location> Locations { get; set; }
    public DbSet<FileMeta> Files { get; set; }

    public static Project? TrackedProject { get; set; }


    public ProjectsContext()
    {
        SQLitePCL.Batteries_V2.Init();

        Database.EnsureCreated();
    }

    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
    {

        optionsBuilder
            .UseSqlite($"Filename={Constants.DatabasePath}");
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Location>().HasData([
            new Location
            {
                LocationId = 1
            },
            new Location
            {
                LocationId = 2
            }
            ]
        );
        modelBuilder.Entity<Contact>().HasData([
                new Contact
                {
                    ContactId = 1
                },
                new Contact
                {
                    ContactId = 2
                }
            ]
        );
        modelBuilder.Entity<Customer>().HasData([
                new Customer
                {
                    CustomerId = 1
                },
            ]
        );
        modelBuilder.Entity<Project>().HasData(
            new Project
            {
                ProjectId = 1,
                IsDefault = true,
                AId = 1,
                BId = 1,
                CustomerId = 1
            }
            );
    }

}