/*
 * This file is part of sc4-dll-utilities, a set of utilities for
 * SimCity 4 DLL Plugins.
 *
 * Copyright (C) 2026 Nicholas Hayes
 *
 * sc4-dll-utilities is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * sc4-dll-utilities is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with sc4-dll-utilities.
 * If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once
#include "StringViewUtil.h"
#include <filesystem>
#include <format>
#include <fstream>
#include <istream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>

namespace detail
{
	struct CaseInsensitiveEquality
	{
		bool operator() (const std::string& s1, const std::string& s2) const
		{
			return StringViewUtil::EqualsIgnoreCase(s1, s2);
		}
	};

	struct CaseInsensitiveHash
	{
		std::size_t operator() (const std::string& value) const
		{
			std::string upperCase(value.length(), ' ');

			std::transform(value.begin(), value.end(), upperCase.begin(), toupper);

			return std::hash<std::string>{}(upperCase);
		}
	};

	namespace Parser
	{
		enum class LineType
		{
			Unknown = 0,
			Comment,
			Section,
			Key
		};

		inline std::tuple<LineType, std::string_view, std::string_view> ParseLine(const std::string_view& line, size_t lineNumber)
		{
			if (!line.empty())
			{
				if (line[0] == ';')
				{
					return std::tuple<LineType, std::string_view, std::string_view>(LineType::Comment, line, {});
				}
				else if (line[0] == '[')
				{
					std::string_view sectionLine = line;
					auto sectionCommentIndex = sectionLine.find_first_of(';');

					if (sectionCommentIndex != std::string_view::npos)
					{
						sectionLine = sectionLine.substr(0, sectionCommentIndex);
					}

					auto closingBracketIndex = sectionLine.find_last_of(']');

					if (closingBracketIndex != std::string_view::npos)
					{
						std::string_view sectionName = sectionLine.substr(1, closingBracketIndex - 1);
						std::string_view trimmedSectionName = StringViewUtil::Trim(sectionName);

						if (trimmedSectionName.empty())
						{
							throw std::runtime_error(std::format(
								"Invalid INI section on line {}: Section name was empty or only white space.",
								lineNumber));
						}

						return std::tuple<LineType, std::string_view, std::string_view>(LineType::Section, trimmedSectionName, {});
					}
					else
					{
						throw std::runtime_error(std::format(
							"Invalid INI section on line {}: Missing the closing bracket.",
							lineNumber));
					}
				}
				else
				{
					auto equalsIndex = line.find_first_of('=');

					if (equalsIndex != std::string_view::npos)
					{
						std::string_view key = StringViewUtil::Trim(line.substr(0, equalsIndex));

						if (key.empty())
						{
							throw std::runtime_error(std::format(
								"Invalid INI key on line {}: The key name was empty or only white space.",
								lineNumber));
						}

						std::string_view value;

						if (equalsIndex < (line.length() - 1))
						{
							value = StringViewUtil::Trim(line.substr(equalsIndex + 1));
						}

						return std::tuple<LineType, std::string_view, std::string_view>(LineType::Key, key, value);
					}
					else
					{
						throw std::runtime_error(std::format(
							"Invalid INI key on line {}: Missing the equals sign.",
							lineNumber));
					}
				}
			}

			return std::tuple<LineType, std::string_view, std::string_view>(LineType::Unknown, {}, {});
		}
	}
}

// An INI file section containing key-value pairs.
class IniSection
{
	friend class IniReader;

private:
	using KeyDataContainer = std::unordered_map<std::string, std::string, detail::CaseInsensitiveHash, detail::CaseInsensitiveEquality>;

	KeyDataContainer values;

	IniSection()
	{
	}

public:
	using const_iterator = KeyDataContainer::const_iterator;

	const_iterator begin() const
	{
		return values.begin();
	}

	const_iterator end() const
	{
		return values.end();
	}

	bool empty() const
	{
		return values.empty();
	}

	size_t size() const
	{
		return values.size();
	}

	const std::string& get_value(const std::string& key) const
	{
		return values.at(key);
	}

	std::string get_value(const std::string& key, std::string defaultValue) const
	{
		auto entry = values.find(key);

		if (entry != values.end())
		{
			return entry->second;
		}

		return defaultValue;
	}

	std::optional<std::string> get_value_optional(const std::string& key) const
	{
		std::optional<std::string> result;

		auto entry = values.find(key);

		if (entry != values.end())
		{
			result = entry->second;
		}

		return result;
	}

	template <typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
	T get_converted_value(const std::string& key) const
	{
		const auto& value = values.at(key);

		T convertedValue{};

		if (!StringViewUtil::TryParse(value, convertedValue))
		{
			throw std::runtime_error(std::format(
				"The {} key value could not be converted to the requested type, value: {}",
				key,
				value));
		}

		return convertedValue;
	}

	template <typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
	T get_converted_value(const std::string& key, T defaultValue) const
	{
		auto entry = values.find(key);

		if (entry != values.end())
		{
			T convertedValue{};

			if (StringViewUtil::TryParse(entry->second, convertedValue))
			{
				return convertedValue;
			}
		}

		return defaultValue;
	}

	template <typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
	std::optional<T> get_converted_value_optional(const std::string& key) const
	{
		std::optional<T> result;

		auto entry = values.find(key);

		if (entry != values.end())
		{
			T convertedValue{};

			if (StringViewUtil::TryParse(entry->second, convertedValue))
			{
				result = convertedValue;
			}
		}

		return result;
	}
};

// Reads the INI file and groups the contained values by section.
//
// Section and key names are case-insensitive and must contain only US-ASCII characters.
// White space is removed from the section and key names when they are read.
// Lines starting with a semicolon are comments, which are ignored.
class IniReader
{
private:
	using SectionContainer = std::unordered_map<std::string, IniSection, detail::CaseInsensitiveHash, detail::CaseInsensitiveEquality>;

	SectionContainer sections;

	void parse_file(std::istream& stream)
	{
		std::string line;
		size_t lineNumber = 1;
		std::string currentSectionName;

		while (std::getline(stream, line))
		{
			auto parsedLine = detail::Parser::ParseLine(line, lineNumber);

			auto lineType = std::get<0>(parsedLine);

			if (lineType == detail::Parser::LineType::Section)
			{
				currentSectionName = std::get<1>(parsedLine);

				sections.emplace(currentSectionName, IniSection());
			}
			else if (lineType == detail::Parser::LineType::Key && !currentSectionName.empty())
			{
				auto& sectionData = sections.at(currentSectionName);

				std::string key(std::get<1>(parsedLine));
				std::string value(std::get<2>(parsedLine));

				sectionData.values.emplace(key, value);
			}

			lineNumber++;
		}
	}

public:
	using const_iterator = SectionContainer::const_iterator;

	IniReader(const std::filesystem::path& path) : sections()
	{
		std::ifstream stream(path);

		parse_file(stream);
	}

	IniReader(std::istream& stream) : sections()
	{
		parse_file(stream);
	}

	const_iterator begin() const
	{
		return sections.begin();
	}

	const_iterator end() const
	{
		return sections.end();
	}

	bool empty() const
	{
		return sections.empty();
	}

	size_t size() const
	{
		return sections.size();
	}

	const IniSection& get_section(const std::string& section) const
	{
		return sections.at(section);
	}

	std::optional<IniSection> get_section_optional(const std::string& section) const
	{
		std::optional<IniSection> result;

		auto entry = sections.find(section);

		if (entry != sections.end())
		{
			result = entry->second;
		}

		return result;
	}

	const IniSection& operator[] (const std::string& section) const
	{
		return get_section(section);
	}
};
