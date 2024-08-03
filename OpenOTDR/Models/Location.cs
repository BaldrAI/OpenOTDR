using CommunityToolkit.Mvvm.ComponentModel;
using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations.Schema;

namespace OpenOTDR.Models;

[Owned]
public partial class Location: ObservableObject
{
    public int LocationId { get; set; }

    [Column("Address")]
    [ObservableProperty] private string? address = string.Empty;

    [Column("Latitude")]
    [ObservableProperty] private double? latitude = 0.0;

    [Column("Longitude")]
    [ObservableProperty]
    private double? longitude = 0.0;

    [Column("CableIn")]
    [ObservableProperty]
    private string? cableIn = string.Empty;

    [Column("FibreIn")]
    [ObservableProperty] private string? fibreIn = string.Empty;

    [Column("CableOut")]
    [ObservableProperty] private string? cableOut = string.Empty;

    [Column("FibreOut")]
    [ObservableProperty] private string? fibreOut = string.Empty;
};