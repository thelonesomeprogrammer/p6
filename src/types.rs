#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct FastBitArray(pub u128);

impl FastBitArray {
    pub const ZERO: Self = Self(0);

    #[inline]
    pub fn set(&mut self, index: usize) {
        self.0 |= 1 << index;
    }

    #[inline]
    pub fn unset(&mut self, index: usize) {
        self.0 &= !(1 << index);
    }

    #[inline]
    pub fn get(&self, index: usize) -> bool {
        (self.0 >> index) & 1 == 1
    }

    #[inline]
    pub fn set_batch<const N: usize>(&mut self, indices: [usize; N]) {
        let mut mask = 0u128;
        for i in indices {
            mask |= 1 << i;
        }
        self.0 |= mask;
    }

    #[inline]
    pub fn unset_batch<const N: usize>(&mut self, indices: [usize; N]) {
        let mut mask = 0u128;
        for i in indices {
            mask |= 1 << i;
        }
        self.0 &= !mask;
    }

    #[inline]
    pub fn any<const N: usize>(&self, indices: [usize; N]) -> bool {
        let mut mask = 0u128;
        for i in indices {
            mask |= 1 << i;
        }
        (self.0 & mask) != 0
    }

    #[inline]
    pub fn all<const N: usize>(&self, indices: [usize; N]) -> bool {
        let mut mask = 0u128;
        for i in indices {
            mask |= 1 << i;
        }
        (self.0 & mask) == mask
    }

    pub fn any_fft(&self) -> bool {
        // Bits: 46 (FftCoefficient), 64 (HumanRangeEnergy), 54 (SpectralCentroid), 
        // 55 (SpectralDistance), 56 (SpectralDecrease), 57 (SpectralSlope), 
        // 60 (SpectrogramCoefficients)
        let mask = (1u128 << 46) | (1u128 << 64) | (1u128 << 54) | (1u128 << 55) | 
                   (1u128 << 56) | (1u128 << 57) | (1u128 << 60);
        (self.0 & mask) != 0
    }
}

impl std::ops::Index<usize> for FastBitArray {
    type Output = bool;

    #[inline]
    fn index(&self, index: usize) -> &Self::Output {
        if (self.0 & (1 << index)) != 0 {
            &true
        } else {
            &false
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Copy)]
pub enum Feature {
    TotalSum,
    Mean,
    Variance,
    Std,
    Min,
    Max,
    Median,
    Skew,
    UnbiasedFisherKurtosis, // tsfresh default
    BiasedFisherKurtosis, // tsfel default
    Mad,
    Iqr,
    Entropy,
    Energy,
    Rms,
    RootMeanSquare,
    ZeroCrossingRate,
    PeakCount,
    AutocorrLag1, // Centered (tsfresh default)
    AutocorrFirst1e, // tsfel 'Autocorrelation' feature
    MeanAbsChange,
    MeanChange,
    CidCe,
    Slope,
    Intercept,
    Paa(u16, u16),
    AbsSumChange,
    CountAboveMean,
    CountBelowMean,
    LongestStrikeAboveMean,
    LongestStrikeBelowMean,
    VariationCoefficient,
    C3(u16),
    Auc,
    SlopeSignChange,
    TurningPoints,
    ZeroCrossingMean,
    ZeroCrossingStd,
    PeakToPeak,
    AbsMax,
    FirstLocMax,
    LastLocMax,
    FirstLocMin,
    LastLocMin,
    Autocorr(u16),
    PartialAutocorr(u16),
    TimeReversalAsymmetry(u16),
    FftCoefficient(u16, FftAttr),
    ApproxEntropy(u8, u32), // r is encoded as u32 (fixed point or bitcast)
    AggLinearTrend(AggAttr, u16, AggFunc),
    Quantile(u32),           // q encoded as u32 bits
    IndexMassQuantile(u32),  // q encoded as u32 bits
    BenfordCorrelation,
    MaxLangevinFixedPoint(u8, u32), // m, r as bits
    SumOfReoccurringValues,
    SumOfReoccurringDataPoints,
    MeanNAbsoluteMax(u16),
    HumanRangeEnergy(u32), // fs as bits
    SpectralCentroid,
    SpectralDistance,
    SpectralDecrease,
    SpectralSlope,
    SignalDistance,
    WaveletFeatures(u16, u16), // mother wavelet, feature type
    SpectrogramCoefficients(u16, u16), // time, freq
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Copy)]
pub enum FftAttr {
    Real,
    Imag,
    Abs,
    Angle,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Copy)]
pub enum AggAttr {
    Slope,
    Intercept,
    Stderr,
    RValue,
    PValue,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Copy)]
pub enum AggFunc {
    Max,
    Min,
    Mean,
    Var,
}

impl From<String> for Feature {
    fn from(s: String) -> Self {
        let s_stripped = if s.starts_with("torque_") {
            &s[7..]
        } else if s.starts_with("value__") {
            &s[7..]
        } else {
            s.as_str()
        };

        match s_stripped {
            "total_sum" | "sum_values" | "Total sum" => Feature::TotalSum,
            "mean" | "Mean" => Feature::Mean,
            "variance" | "Variance" => Feature::Variance,
            "std" | "std_dev" | "standard_deviation" | "Standard deviation" => Feature::Std,
            "min" | "minimum" | "Min" | "min_value" => Feature::Min,
            "max" | "maximum" | "Max" | "max_value" => Feature::Max,
            "median" | "Median" => Feature::Median,
            "skew" | "skewness" | "Skewness" => Feature::Skew,
            "kurtosis" | "unbiased_fisher_kurtosis" | "Kurtosis" => Feature::UnbiasedFisherKurtosis,
            "biased_fisher_kurtosis" => Feature::BiasedFisherKurtosis,
            "mad" | "Mean absolute deviation" => Feature::Mad,
            "iqr" | "Interquartile range" => Feature::Iqr,
            "entropy" | "Entropy" => Feature::Entropy,
            "energy" | "Absolute energy" | "abs_energy" => Feature::Energy,
            "rms" | "Root mean square" => Feature::Rms,
            "root_mean_square" => Feature::RootMeanSquare,
            "zero_crossing_rate" | "Zero crossing rate" => Feature::ZeroCrossingRate,
            "peak_count" | "Peak count" => Feature::PeakCount,
            "autocorr_lag1" | "centered_autocorr_lag1" => Feature::AutocorrLag1,
            "autocorrelation" | "autocorr_first_1e" | "Autocorrelation" => Feature::AutocorrFirst1e,
            "mean_abs_change" | "Mean absolute change" => Feature::MeanAbsChange,
            "mean_change" | "mean_diff" | "Mean diff" => Feature::MeanChange,
            "cid_ce" | "Complexity invariant distance" => Feature::CidCe,
            "slope" | "Slope" => Feature::Slope,
            "intercept" | "Intercept" => Feature::Intercept,
            "abs_sum_change" | "Absolute sum change" => Feature::AbsSumChange,
            "count_above_mean" | "Count above mean" => Feature::CountAboveMean,
            "count_below_mean" | "Count below mean" => Feature::CountBelowMean,
            "longest_strike_above_mean" | "Longest strike above mean" => {
                Feature::LongestStrikeAboveMean
            }
            "longest_strike_below_mean" | "Longest strike below mean" => {
                Feature::LongestStrikeBelowMean
            }
            "variation_coefficient" | "Variation coefficient" => Feature::VariationCoefficient,
            "auc" | "Area under the curve" => Feature::Auc,
            "slope_sign_change" | "Slope sign change" => Feature::SlopeSignChange,
            "turning_points" | "Turning points" => Feature::TurningPoints,
            "zero_crossing_mean" | "Zero crossing mean" => Feature::ZeroCrossingMean,
            "zero_crossing_std" | "Zero crossing std" => Feature::ZeroCrossingStd,
            "peak_to_peak" | "Peak to peak distance" | "Peak to peak" => Feature::PeakToPeak,
            "abs_max" | "absolute_maximum" | "Absolute maximum" => Feature::AbsMax,
            "first_loc_max" | "first_location_of_maximum" | "First location of maximum" => {
                Feature::FirstLocMax
            }
            "last_loc_max" | "last_location_of_maximum" | "Last location of maximum" => {
                Feature::LastLocMax
            }
            "first_loc_min" | "first_location_of_minimum" | "First location of minimum" => {
                Feature::FirstLocMin
            }
            "last_loc_min" | "last_location_of_minimum" | "Last location of minimum" => {
                Feature::LastLocMin
            }
            "benford_correlation" => Feature::BenfordCorrelation,
            "sum_of_reoccurring_values" => Feature::SumOfReoccurringValues,
            "sum_of_reoccurring_data_points" => Feature::SumOfReoccurringDataPoints,
            "spectral_centroid" | "Centroid" | "Spectral centroid" => Feature::SpectralCentroid,
            "spectral_distance" | "Spectral distance" => Feature::SpectralDistance,
            "spectral_decrease" | "Spectral decrease" => Feature::SpectralDecrease,
            "spectral_slope" | "Spectral slope" => Feature::SpectralSlope,
            "signal_distance" | "Signal distance" => Feature::SignalDistance,
            "human_range_energy" | "Human range energy" => {
                Feature::HumanRangeEnergy(833.0f32.to_bits())
            }
            "average_power" | "Average power" => Feature::Energy,
            e => {
                if let Some(arg) = e.strip_prefix("human_range_energy-") {
                    if let Ok(fs) = arg.parse::<f32>() {
                        return Feature::HumanRangeEnergy(fs.to_bits());
                    }
                } else if let Some(arg) = e.strip_prefix("paa-") {
                    let params: Vec<&str> = arg.split('-').collect();
                    if params.len() == 2 {
                        if let (Ok(n), Ok(m)) = (params[0].parse::<u16>(), params[1].parse::<u16>()) {
                            return Feature::Paa(n, m);
                        }
                    }
                } else if let Some(arg) = e.strip_prefix("c3-") {
                    let param = arg.trim();
                    if let Ok(n) = param.parse::<u16>() {
                        return Feature::C3(n);
                    }
                } else if e.contains("c3__lag_") {
                    if let Some(pos) = e.find("lag_") {
                        if let Ok(n) = e[pos+4..].parse::<u16>() {
                            return Feature::C3(n);
                        }
                    }
                } else if let Some(arg) = e.strip_prefix("autocorr-") {
                    if let Ok(n) = arg.parse::<u16>() {
                        return Feature::Autocorr(n);
                    }
                } else if let Some(arg) = e.strip_prefix("partial_autocorr-") {
                    if let Ok(n) = arg.parse::<u16>() {
                        return Feature::PartialAutocorr(n);
                    }
                } else if let Some(arg) = e.strip_prefix("time_reversal_asymmetry-") {
                    if let Ok(n) = arg.parse::<u16>() {
                        return Feature::TimeReversalAsymmetry(n);
                    }
                } else if e.contains("time_reversal_asymmetry_statistic__lag_") {
                    if let Some(pos) = e.find("lag_") {
                        if let Ok(n) = e[pos+4..].parse::<u16>() {
                            return Feature::TimeReversalAsymmetry(n);
                        }
                    }
                } else if let Some(arg) = e.strip_prefix("fft_coeff-") {
                    let params: Vec<&str> = arg.split('-').collect();
                    if params.len() == 2 {
                        if let Ok(coeff) = params[0].parse::<u16>() {
                            let attr = match params[1] {
                                "real" => FftAttr::Real,
                                "imag" => FftAttr::Imag,
                                "abs" => FftAttr::Abs,
                                "angle" => FftAttr::Angle,
                                _ => panic!("Unknown FFT attribute: {}", params[1]),
                            };
                            return Feature::FftCoefficient(coeff, attr);
                        }
                    }
                } else if let Some(arg) = e.strip_prefix("approx_entropy-") {
                    let params: Vec<&str> = arg.split('-').collect();
                    if params.len() == 2 {
                        if let (Ok(m), Ok(r)) = (params[0].parse::<u8>(), params[1].parse::<f32>()) {
                            return Feature::ApproxEntropy(m, r.to_bits());
                        }
                    }
                } else if let Some(arg) = e.strip_prefix("agg_linear_trend-") {
                    let params: Vec<&str> = arg.split('-').collect();
                    if params.len() == 3 {
                        let attr = match params[0] {
                            "slope" => AggAttr::Slope,
                            "intercept" => AggAttr::Intercept,
                            "stderr" => AggAttr::Stderr,
                            "rvalue" => AggAttr::RValue,
                            "pvalue" => AggAttr::PValue,
                            _ => panic!("Unknown Agg attribute: {}", params[0]),
                        };
                        if let Ok(chunk_len) = params[1].parse::<u16>() {
                            let func = match params[2] {
                                "max" => AggFunc::Max,
                                "min" => AggFunc::Min,
                                "mean" => AggFunc::Mean,
                                "var" => AggFunc::Var,
                                _ => panic!("Unknown Agg function: {}", params[2]),
                            };
                            return Feature::AggLinearTrend(attr, chunk_len, func);
                        }
                    }
                } else if e.contains("agg_linear_trend__attr_") {
                    // value__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"mean"
                    let attr = if e.contains("attr_\"slope\"") { AggAttr::Slope }
                              else if e.contains("attr_\"intercept\"") { AggAttr::Intercept }
                              else { AggAttr::Slope };
                    
                    let chunk_len = if let Some(pos) = e.find("chunk_len_") {
                        let sub = &e[pos+10..];
                        let end = sub.find("__").unwrap_or(sub.len());
                        sub[..end].parse::<u16>().unwrap_or(5)
                    } else { 5 };

                    let func = if e.contains("f_agg_\"mean\"") { AggFunc::Mean }
                               else if e.contains("f_agg_\"var\"") { AggFunc::Var }
                               else if e.contains("f_agg_\"max\"") { AggFunc::Max }
                               else if e.contains("f_agg_\"min\"") { AggFunc::Min }
                               else { AggFunc::Mean };
                    
                    return Feature::AggLinearTrend(attr, chunk_len, func);
                } else if e.contains("linear_trend__attr_") {
                    let attr = if e.contains("attr_\"slope\"") {
                        AggAttr::Slope
                    } else if e.contains("attr_\"intercept\"") {
                        AggAttr::Intercept
                    } else if e.contains("attr_\"rvalue\"") {
                        AggAttr::RValue
                    } else if e.contains("attr_\"stderr\"") {
                        AggAttr::Stderr
                    } else {
                        AggAttr::Slope
                    };
                    let chunk_len = if let Some(pos) = e.find("chunk_len_") {
                        let sub = &e[pos + 10..];
                        let end = sub.find("__").unwrap_or(sub.len());
                        sub[..end].parse::<u16>().unwrap_or(1)
                    } else {
                        1
                    };
                    return Feature::AggLinearTrend(attr, chunk_len, AggFunc::Mean);
                } else if let Some(arg) = e.strip_prefix("quantile-") {
                    if let Ok(q) = arg.parse::<f32>() {
                        return Feature::Quantile(q.to_bits());
                    }
                } else if e.contains("quantile__q_") {
                    if let Some(pos) = e.find("q_") {
                        if let Ok(q) = e[pos+2..].parse::<f32>() {
                            return Feature::Quantile(q.to_bits());
                        }
                    }
                } else if let Some(arg) = e.strip_prefix("index_mass_quantile-") {
                    if let Ok(q) = arg.parse::<f32>() {
                        return Feature::IndexMassQuantile(q.to_bits());
                    }
                } else if e.contains("index_mass_quantile__q_") {
                    if let Some(pos) = e.find("q_") {
                        if let Ok(q) = e[pos+2..].parse::<f32>() {
                            return Feature::IndexMassQuantile(q.to_bits());
                        }
                    }
                } else if let Some(arg) = e.strip_prefix("max_langevin_fixed_point-") {
                    let params: Vec<&str> = arg.split('-').collect();
                    if params.len() == 2 {
                        if let (Ok(m), Ok(r)) = (params[0].parse::<u8>(), params[1].parse::<f32>()) {
                            return Feature::MaxLangevinFixedPoint(m, r.to_bits());
                        }
                    }
                } else if e.contains("max_langevin_fixed_point__m_") {
                    // value__max_langevin_fixed_point__m_3__r_30
                    let m = if let Some(pos) = e.find("m_") {
                        let sub = &e[pos+2..];
                        let end = sub.find("__").unwrap_or(sub.len());
                        sub[..end].parse::<u8>().unwrap_or(3)
                    } else { 3 };
                    let r = if let Some(pos) = e.find("r_") {
                        let sub = &e[pos+2..];
                        let end = sub.find("__").unwrap_or(sub.len());
                        sub[..end].parse::<f32>().unwrap_or(30.0)
                    } else { 30.0 };
                    return Feature::MaxLangevinFixedPoint(m, r.to_bits());
                } else if e.contains("mean_n_absolute_max__number_of_maxima_") {
                    if let Some(pos) = e.find("number_of_maxima_") {
                        if let Ok(n) = e[pos+17..].parse::<u16>() {
                            return Feature::MeanNAbsoluteMax(n);
                        }
                    }
                } else if let Some(arg) = e.strip_prefix("mean_n_absolute_max-") {
                    if let Ok(n) = arg.parse::<u16>() {
                        return Feature::MeanNAbsoluteMax(n);
                    }
                } else if let Some(arg) = e.strip_prefix("wavelet-") {
                    let params: Vec<&str> = arg.split('-').collect();
                    if params.len() == 2 {
                        if let (Ok(w), Ok(f)) =
                            (params[0].parse::<u16>(), params[1].parse::<u16>())
                        {
                            return Feature::WaveletFeatures(w, f);
                        }
                    }
                } else if e.contains("Wavelet") {
                    // Wavelet absolute mean_104.17Hz
                    // Wavelet variance_104.17Hz
                    let f_type = if e.contains("absolute mean") { 0 } else { 1 };
                    let freq = if let Some(pos) = e.find('_') {
                        if let Some(end) = e.find("Hz") {
                            e[pos + 1..end].parse::<f32>().unwrap_or(0.0)
                        } else {
                            0.0
                        }
                    } else {
                        0.0
                    };
                    return Feature::WaveletFeatures(freq.to_bits() as u16, f_type); // Hacky storage
                } else if let Some(arg) = e.strip_prefix("spectrogram-") {
                    let params: Vec<&str> = arg.split('-').collect();
                    if params.len() == 2 {
                        if let (Ok(t), Ok(f)) = (params[0].parse::<u16>(), params[1].parse::<u16>())
                        {
                            return Feature::SpectrogramCoefficients(t, f);
                        }
                    }
                } else if e.contains("Spectrogram mean coefficient_") {
                    // Spectrogram mean coefficient_322.58Hz
                    if let Some(pos) = e.rfind('_') {
                        if let Some(end) = e.find("Hz") {
                            let freq = e[pos + 1..end].parse::<f32>().unwrap_or(0.0);
                            return Feature::SpectrogramCoefficients(0, freq.to_bits() as u16); // Hacky
                        }
                    }
                }
                panic!("Unknown feature: {}", e);
            }
        }
    }
}

impl Feature {
    pub fn name(&self) -> String {
        match self {
            Feature::TotalSum => "total_sum".to_string(),
            Feature::Mean => "mean".to_string(),
            Feature::Variance => "variance".to_string(),
            Feature::Std => "std_dev".to_string(),
            Feature::Min => "min_value".to_string(),
            Feature::Max => "max_value".to_string(),
            Feature::Median => "median".to_string(),
            Feature::Skew => "skew".to_string(),
            Feature::UnbiasedFisherKurtosis => "unbiased_fisher_kurtosis".to_string(),
            Feature::BiasedFisherKurtosis => "biased_fisher_kurtosis".to_string(),
            Feature::Mad => "mad".to_string(),
            Feature::Iqr => "iqr".to_string(),
            Feature::Entropy => "entropy".to_string(),
            Feature::Energy => "energy".to_string(),
            Feature::Rms => "rms".to_string(),
            Feature::RootMeanSquare => "root_mean_square".to_string(),
            Feature::ZeroCrossingRate => "zero_crossing_rate".to_string(),
            Feature::PeakCount => "peak_count".to_string(),
            Feature::AutocorrLag1 => "autocorr_lag1".to_string(),
            Feature::AutocorrFirst1e => "autocorrelation".to_string(),
            Feature::MeanAbsChange => "mean_abs_change".to_string(),
            Feature::MeanChange => "mean_change".to_string(),
            Feature::CidCe => "cid_ce".to_string(),
            Feature::Slope => "slope".to_string(),
            Feature::Intercept => "intercept".to_string(),
            Feature::AbsSumChange => "abs_sum_change".to_string(),
            Feature::CountAboveMean => "count_above_mean".to_string(),
            Feature::CountBelowMean => "count_below_mean".to_string(),
            Feature::LongestStrikeAboveMean => "longest_strike_above_mean".to_string(),
            Feature::LongestStrikeBelowMean => "longest_strike_below_mean".to_string(),
            Feature::VariationCoefficient => "variation_coefficient".to_string(),
            Feature::Auc => "auc".to_string(),
            Feature::SlopeSignChange => "slope_sign_change".to_string(),
            Feature::TurningPoints => "turning_points".to_string(),
            Feature::ZeroCrossingMean => "zero_crossing_mean".to_string(),
            Feature::ZeroCrossingStd => "zero_crossing_std".to_string(),
            Feature::PeakToPeak => "peak_to_peak".to_string(),
            Feature::C3(lag) => format!("c3-{}", lag),
            Feature::Paa(total, index) => format!("paa-{}-{}", total, index),
            Feature::AbsMax => "abs_max".to_string(),
            Feature::FirstLocMax => "first_loc_max".to_string(),
            Feature::LastLocMax => "last_loc_max".to_string(),
            Feature::FirstLocMin => "first_loc_min".to_string(),
            Feature::LastLocMin => "last_loc_min".to_string(),
            Feature::Autocorr(lag) => format!("autocorr-{}", lag),
            Feature::PartialAutocorr(lag) => format!("partial_autocorr-{}", lag),
            Feature::TimeReversalAsymmetry(lag) => format!("time_reversal_asymmetry-{}", lag),
            Feature::FftCoefficient(coeff, attr) => {
                let attr_str = match attr {
                    FftAttr::Real => "real",
                    FftAttr::Imag => "imag",
                    FftAttr::Abs => "abs",
                    FftAttr::Angle => "angle",
                };
                format!("fft_coeff-{}-{}", coeff, attr_str)
            }
            Feature::ApproxEntropy(m, r_bits) => {
                format!("approx_entropy-{}-{}", m, f32::from_bits(*r_bits))
            }
            Feature::AggLinearTrend(attr, chunk_len, func) => {
                let attr_str = match attr {
                    AggAttr::Slope => "slope",
                    AggAttr::Intercept => "intercept",
                    AggAttr::Stderr => "stderr",
                    AggAttr::RValue => "rvalue",
                    AggAttr::PValue => "pvalue",
                };
                let func_str = match func {
                    AggFunc::Max => "max",
                    AggFunc::Min => "min",
                    AggFunc::Mean => "mean",
                    AggFunc::Var => "var",
                };
                format!("agg_linear_trend-{}-{}-{}", attr_str, chunk_len, func_str)
            }
            Feature::Quantile(q_bits) => format!("quantile-{}", f32::from_bits(*q_bits)),
            Feature::IndexMassQuantile(q_bits) => {
                format!("index_mass_quantile-{}", f32::from_bits(*q_bits))
            }
            Feature::BenfordCorrelation => "benford_correlation".to_string(),
            Feature::MaxLangevinFixedPoint(m, r_bits) => {
                format!("max_langevin_fixed_point-{}-{}", m, f32::from_bits(*r_bits))
            }
            Feature::SumOfReoccurringValues => "sum_of_reoccurring_values".to_string(),
            Feature::SumOfReoccurringDataPoints => "sum_of_reoccurring_data_points".to_string(),
            Feature::MeanNAbsoluteMax(n) => format!("mean_n_absolute_max-{}", n),
            Feature::HumanRangeEnergy(fs_bits) => format!("human_range_energy-{}", f32::from_bits(*fs_bits)),
            Feature::SpectralCentroid => "spectral_centroid".to_string(),
            Feature::SpectralDistance => "spectral_distance".to_string(),
            Feature::SpectralDecrease => "spectral_decrease".to_string(),
            Feature::SpectralSlope => "spectral_slope".to_string(),
            Feature::SignalDistance => "signal_distance".to_string(),
            Feature::WaveletFeatures(w, f) => format!("wavelet-{}-{}", w, f),
            Feature::SpectrogramCoefficients(t, f) => format!("spectrogram-{}-{}", t, f),
        }
    }
}
